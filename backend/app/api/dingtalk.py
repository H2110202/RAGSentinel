from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.department import Department, user_departments
from pydantic import BaseModel
from typing import Optional
import httpx
import os

router = APIRouter()

class DingtalkConfig(BaseModel):
    appid: str
    appsecret: str

async def get_token(client: httpx.AsyncClient, appid: str, appsecret: str):
    resp = await client.get(
        "https://oapi.dingtalk.com/gettoken",
        params={"appkey": appid, "appsecret": appsecret},
        timeout=10
    )
    data = resp.json()
    if data.get("errcode") != 0:
        raise Exception(f"获取Token失败: {data.get('errmsg', '')}")
    return data["access_token"]

async def dingtalk_post(client: httpx.AsyncClient, path: str, body: dict, token: str):
    resp = await client.post(
        f"https://oapi.dingtalk.com{path}",
        params={"access_token": token},
        json=body,
        timeout=15
    )
    return resp.json()

@router.post("/dingtalk/test")
async def test_dingtalk(cfg: DingtalkConfig):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                "https://oapi.dingtalk.com/gettoken",
                params={"appkey": cfg.appid, "appsecret": cfg.appsecret}
            )
            data = resp.json()
            if data.get("errcode") == 0:
                return {"success": True, "message": "连接成功！钉钉配置有效"}
            else:
                return {"success": False, "message": f"连接失败: {data.get('errmsg', '未知错误')}"}
        except httpx.ConnectError:
            return {"success": False, "message": "无法连接到钉钉服务器，请检查网络"}
        except Exception as e:
            return {"success": False, "message": f"连接异常: {str(e)}"}

@router.get("/dingtalk/qrurl")
async def get_dingtalk_qrurl(appid: Optional[str] = None):
    from urllib.parse import urlencode
    from app.core.config import config
    aid = appid or config.DINGTALK_APPID
    if not aid:
        return {"success": False, "message": "未配置AppID"}
    params = urlencode({
        "appid": aid, "response_type": "code", "scope": "openid",
        "state": "perm_admin",
        "redirect_uri": os.getenv("DINGTALK_REDIRECT_URI", "http://localhost:8088/api/auth/dingtalk/callback")
    })
    return {"success": True, "qrurl": f"https://login.dingtalk.com/oauth2/auth?{params}"}

@router.post("/dingtalk/sync")
async def sync_dingtalk_org(cfg: DingtalkConfig, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            token = await get_token(client, cfg.appid, cfg.appsecret)

            async def get_all_depts(parent_id=1, depth=0):
                if depth > 15:
                    return []
                r = await dingtalk_post(client, "/topapi/v2/department/listsub", {"dept_id": parent_id}, token)
                if r.get("errcode") != 0:
                    return []
                results = []
                for d in r.get("result", []):
                    results.append(d)
                    results.extend(await get_all_depts(d["dept_id"], depth + 1))
                return results

            all_depts = await get_all_depts(1)

            dept_map = {}
            dept_created = 0
            dept_updated = 0

            for dept in all_depts:
                dt_id = str(dept.get("dept_id"))
                existing = db.query(Department).filter(Department.dingtalk_id == dt_id).first()
                if existing:
                    existing.name = dept.get("name", existing.name)
                    existing.code = dt_id
                    dept_updated += 1
                    dept_map[dt_id] = existing
                else:
                    new_dept = Department(
                        name=dept.get("name", ""),
                        code=dt_id,
                        dingtalk_id=dt_id,
                    )
                    db.add(new_dept)
                    db.flush()
                    dept_created += 1
                    dept_map[dt_id] = new_dept

            root_dept = db.query(Department).filter(Department.dingtalk_id == "1").first()
            if not root_dept:
                root_dept = Department(name="根部门", code="1", dingtalk_id="1")
                db.add(root_dept)
                db.flush()
                dept_created += 1
            dept_map["1"] = root_dept

            for dept in all_depts:
                dt_id = str(dept.get("dept_id"))
                dt_parent_id = str(dept.get("parent_id", "1"))
                db_dept = dept_map.get(dt_id)
                if db_dept:
                    parent_db_dept = dept_map.get(dt_parent_id)
                    db_dept.parent_id = parent_db_dept.id if parent_db_dept else None

            db.execute(user_departments.delete())
            db.commit()

            all_users_data = {}
            for dept in all_depts:
                dt_id = dept.get("dept_id")
                cursor = 0
                has_more = True
                while has_more:
                    r = await dingtalk_post(client, "/topapi/v2/user/list", {
                        "dept_id": dt_id, "cursor": cursor, "size": 100
                    }, token)
                    if r.get("errcode") != 0:
                        break
                    for u in r.get("result", {}).get("list", []):
                        userid = u.get("userid", "")
                        if userid and userid not in all_users_data:
                            all_users_data[userid] = u
                    has_more = r.get("result", {}).get("has_more", False)
                    cursor = r.get("result", {}).get("next_cursor", 0)

            user_created = 0
            user_updated = 0

            for userid, u in all_users_data.items():
                expected_username = f"dingtalk_{userid}"
                existing_user = db.query(User).filter(
                    (User.dingtalk_userid == userid) | (User.username == expected_username)
                ).first()

                if existing_user:
                    existing_user.dingtalk_userid = userid
                    existing_user.full_name = u.get("name", existing_user.full_name)
                    existing_user.email = u.get("email", existing_user.email) or existing_user.email
                    existing_user.username = expected_username
                    existing_user.is_active = u.get("active", True)
                    user_updated += 1
                else:
                    existing_user = User(
                        username=expected_username,
                        full_name=u.get("name", ""),
                        dingtalk_userid=userid,
                        email=u.get("email", ""),
                        is_active=u.get("active", True),
                        hashed_password="*"
                    )
                    db.add(existing_user)
                    db.flush()
                    user_created += 1

                dept_ids = u.get("dept_id_list", [])
                for dt_did in dept_ids:
                    dt_did_str = str(dt_did)
                    db_dept = dept_map.get(dt_did_str)
                    if db_dept:
                        exists = db.execute(
                            user_departments.select().where(
                                (user_departments.c.user_id == existing_user.id) &
                                (user_departments.c.department_id == db_dept.id)
                            )
                        ).fetchone()
                        if not exists:
                            db.execute(user_departments.insert().values(
                                user_id=existing_user.id,
                                department_id=db_dept.id
                            ))

            db.commit()

            total_depts = db.query(Department).filter(Department.is_active == True).count()
            total_users = db.query(User).filter(User.is_active == True).count()

            return {
                "success": True,
                "message": f"同步完成！部门: 新增{dept_created}/更新{dept_updated}, 人员: 新增{user_created}/更新{user_updated}, 总计{total_depts}个部门{total_users}人",
                "departments_count": total_depts,
                "users_count": total_users
            }
    except Exception as e:
        import traceback
        return {"success": False, "message": f"同步异常: {str(e)}\n{traceback.format_exc()}"}
