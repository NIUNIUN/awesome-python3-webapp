#!/usr/bin/env.python
# -*- coding: utf-8 -*-

'''
Models for user, blog, comment.
'''

__author__ = 'tang_xqing'

import time,uuid

from www.orm import Model,StringField,BooleanField,FloatField,TextField

def next_id():
    return '%015d%s000' %(int(time.time() * 1000),uuid.uuid4().hex)

class User(Model):
    __table__= 'users'

    id = StringField(primary_key=True,default=next_id,ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    create_at = FloatField(default=time.time)

class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True,default=next_id,ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    create_at = FloatField(default= time.time)

class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True,default=next_id,ddl='varchar(50)')
    blog_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    create_at = FloatField(default=time.time)

'''
 default可以作为函数对象传入，在调用svae()时自动计算

 日期和时间：使用float类型存储，而不是datatime类型。
        好处：是不必关心数据库的时区以及时区转换问题，排序非常简单，显示的时候，只需要做一个float到str的转换，也非常容易。
'''



