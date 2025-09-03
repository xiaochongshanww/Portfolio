"""
媒体库权限控制工具
"""
from flask import request
from sqlalchemy import or_
from ..models import Media, MediaFolder
from .. import db

def get_media_query_for_user(user_id: int, user_role: str):
    """根据用户角色返回相应的媒体查询条件"""
    base_query = Media.query
    
    if user_role == 'admin':
        # 管理员：看到所有媒体
        return base_query
        
    elif user_role == 'editor':
        # 编辑者：看到自己的 + shared/public 的媒体
        return base_query.filter(
            or_(
                Media.owner_id == user_id,  # 自己的
                Media.visibility.in_(['shared', 'public'])  # 共享的
            )
        )
        
    elif user_role == 'author':
        # 作者：看到自己的 + public 的媒体
        return base_query.filter(
            or_(
                Media.owner_id == user_id,  # 自己的
                Media.visibility == 'public'  # 公开的
            )
        )
    
    else:
        # 未知角色：无权限
        return base_query.filter(False)


def get_folder_query_for_user(user_id: int, user_role: str):
    """根据用户角色返回相应的文件夹查询条件"""
    base_query = MediaFolder.query
    
    if user_role == 'admin':
        # 管理员：看到所有文件夹
        return base_query
        
    elif user_role == 'editor':
        # 编辑者：看到自己的 + shared/public 的文件夹
        return base_query.filter(
            or_(
                MediaFolder.owner_id == user_id,  # 自己的
                MediaFolder.visibility.in_(['shared', 'public'])  # 共享的
            )
        )
        
    elif user_role == 'author':
        # 作者：看到自己的 + public 的文件夹
        return base_query.filter(
            or_(
                MediaFolder.owner_id == user_id,  # 自己的
                MediaFolder.visibility == 'public'  # 公开的
            )
        )
    
    else:
        # 未知角色：无权限
        return base_query.filter(False)


def can_view_media(media: Media, user_id: int, user_role: str) -> bool:
    """检查用户是否可以查看媒体"""
    if user_role == 'admin':
        return True  # 管理员可以查看所有
    if media.owner_id == user_id:
        return True  # 所有者可以查看自己的
    if media.visibility == 'public':
        return True  # 任何人都可以查看公开的
    if media.visibility == 'shared' and user_role in ['editor']:
        return True  # 编辑者可以查看共享的
    return False


def can_modify_media(media: Media, user_id: int, user_role: str) -> bool:
    """检查用户是否可以修改媒体"""
    if user_role == 'admin':
        return True  # 管理员可以修改所有
    if media.owner_id == user_id:
        return True  # 所有者可以修改自己的
    return False


def can_delete_media(media: Media, user_id: int, user_role: str) -> bool:
    """检查用户是否可以删除媒体"""
    if user_role == 'admin':
        return True  # 管理员可以删除所有
    if media.owner_id == user_id:
        return True  # 所有者可以删除自己的
    return False


def can_view_folder(folder: MediaFolder, user_id: int, user_role: str) -> bool:
    """检查用户是否可以查看文件夹"""
    if user_role == 'admin':
        return True  # 管理员可以查看所有
    if folder.owner_id == user_id:
        return True  # 所有者可以查看自己的
    if folder.visibility == 'public':
        return True  # 任何人都可以查看公开的
    if folder.visibility == 'shared' and user_role in ['editor']:
        return True  # 编辑者可以查看共享的
    return False


def can_modify_folder(folder: MediaFolder, user_id: int, user_role: str) -> bool:
    """检查用户是否可以修改文件夹"""
    if user_role == 'admin':
        return True  # 管理员可以修改所有
    if folder.owner_id == user_id:
        return True  # 所有者可以修改自己的
    return False


def can_delete_folder(folder: MediaFolder, user_id: int, user_role: str) -> bool:
    """检查用户是否可以删除文件夹"""
    if user_role == 'admin':
        return True  # 管理员可以删除所有
    if folder.owner_id == user_id:
        return True  # 所有者可以删除自己的
    return False


def filter_media_by_permissions(query, user_id: int, user_role: str):
    """为查询添加权限过滤"""
    if user_role == 'admin':
        return query  # 管理员看所有
    elif user_role == 'editor':
        return query.filter(
            or_(
                Media.owner_id == user_id,
                Media.visibility.in_(['shared', 'public'])
            )
        )
    elif user_role == 'author':
        return query.filter(
            or_(
                Media.owner_id == user_id,
                Media.visibility == 'public'
            )
        )
    else:
        return query.filter(False)