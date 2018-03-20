#!/usr/bin/env.python
# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level=logging.INFO)

import asyncio,os,json,time
from datetime import datetime
from aiohttp import web
#
# def index(request):
#     return web.Response(body=b'<h1>Index</h1>', content_type='text/html')
#
# @asyncio.coroutine
# def init(loop):
#     app = web.Application(loop = loop)
#     app.router.add_route('GET','/',index)
#     srv = yield from loop.create_server(app.make_handler(),'127.0.0.1',9000)
#     logging.info('Server started at http://127.0.0.1:9000...')
#     return srv
#
# loop = asyncio.get_event_loop()
# loop.run_until_complete(init(loop))
# loop.run_forever()

import www.orm
from www.models import User,Blog,Comment
from www.orm import Model,StringField,IntegerField

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
import sys

def test(loop):
    yield from www.orm.create_pool(loop = loop,user='root', password='123456789', db='awesome')

    u = User(name='Test', email='test@example.com', passwd='1234567890', image='about:blank')

    yield from u.save()

# for x in test():
#     pass

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.wait([test(loop)]))
    loop.close()
    if loop.is_closed():
        sys.exit(0)