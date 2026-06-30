import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from models import User
from utils.security import get_password_hash


def create_admin():
    db = SessionLocal()
    try:
        admin_user_id = "admin"
        admin_password = "admin123"

        existing = db.query(User).filter(User.user_id == admin_user_id).first()
        if existing:
            if not existing.is_admin:
                existing.is_admin = True
                existing.password_hash = get_password_hash(admin_password)
                existing.nickname = "超级管理员"
                db.commit()
                print(f"✅ 已将用户 {admin_user_id} 设为管理员")
            else:
                print(f"ℹ️  管理员账号 {admin_user_id} 已存在")
        else:
            admin = User(
                user_id=admin_user_id,
                openid="admin_openid",
                nickname="超级管理员",
                phone="admin",
                is_vip=True,
                is_admin=True,
                is_buyer=False,
                status="active",
                password_hash=get_password_hash(admin_password)
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"✅ 管理员账号创建成功！")
            print(f"   账号: {admin_user_id}")
            print(f"   密码: {admin_password}")
            print(f"   请登录后及时修改密码！")

    except Exception as e:
        print(f"❌ 创建失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
