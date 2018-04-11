#!/usr/bin/env.python
# -*- coding: utf-8 -*-

# import www.orm
# from www.models import User,Blog,Comment
# from www.orm import Model,StringField,IntegerField
#
# class User2(Model):
#     __table__ = 'user2'
#     id = IntegerField(primary_key=True)
#     name = StringField()
#
# # 创建实例:
# user = User2(id=123, name='Michael')
# # 存入数据库:
# user.insert()
# # 查询所有User对象:
# users = User.findAll()

import asyncio

import sys

from www import orm
from www.models import User, Blog, Comment

@asyncio.coroutine
def test(loop):
    db_dict = {'user':'root','password':'123456789','db':'awesome'}
    yield from orm.create_pool(loop= loop,**db_dict)
    # yield from orm.create_pool(user='www-data', password='www-data', database='awesome')

    u = User(name='Test', email='test@example.com', passwd='1234567890', image='about:blank')

    yield from u.save()
    yield from orm.destory_pool()

# for x in test():
#     pass
if __name__ == '__main__':
    pass
    # loop = asyncio.get_event_loop()
    # loop.run_until_complete(test(loop))
    # loop.close()
    # if loop.is_closed():
    #     sys.exit(0)

@asyncio.coroutine
def test(loop,**kw):
    yield from orm.create_pool(loop=loop,user='root', password='123456789', db='awesome')
    u = User(name=kw.get('name'), email=kw.get('email'), passwd=kw.get('passwd'), image=kw.get('image'))
    yield from u.save()
    yield from orm.destory_pool()

# data=dict(name='gaf', email='1234@qq.com', passwd='1312345', image='about:blank')
# loop=asyncio.get_event_loop()
# loop.run_until_complete(test(loop,**data))
# loop.close()