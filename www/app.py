#!/usr/bin/env.python
# -*- coding: utf-8 -*-

import logging; logging.basicConfig(level=logging.INFO)
import asyncio,os,json,time
import www.orm
from www.coroweb import add_static,add_routes
from datetime import datetime
from aiohttp import web
from jinja2 import Environment,FileSystemLoader

def init_jinja2(app,**kw):
    logging.info('init jinja2...')
    options = dict(
        autoescape = kw.get('autoescape',True),
        block_start_string = kw.get('block_start_string','{%'),
        block_end_string = kw.get('block_end_string','%}'),
        variable_start_string = kw.get('variable_start_string','{{'),
        variable_end_string = kw.get('variable_end_string','}}'),
        auto_reload = kw.get('auto_reload',True)
    )
    path = kw.get('path', None)
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)

    env = Environment(loader=FileSystemLoader(path), **options)
    filters = kw.get('filters', None)
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env

@asyncio.coroutine
def logger_factory(app, handler):
    @asyncio.coroutine
    def logger(request):
        # 请求前，记录
        logging.info('Request: %s %s' % (request.method, request.path))
        # yield from asyncio.sleep(0.3)
        # 继续处理请求
        return (yield from handler(request))
    return logger

@asyncio.coroutine
def data_factory(app,handler):
    @asyncio.coroutine
    def parse_data(request):
        if request.method == 'POST':
            if request.content_type.startswith('application/json'):
                request.__data__ = yield from request.json()
                logging.info('Request json: %s' % str(request.__data__))

            elif request.content_type.startswith('application/x-www-form-urlencoded'):
                request.__data__ = yield from request.post()
                logging.info('Request form: %s' % str(request.__data__))

        return (yield from handler(request))
    return parse_data

@asyncio.coroutine
def response_factory(app,handler):
    @asyncio.coroutine
    def response(request):
        # 结果
        r = yield from handler(request)

        if isinstance(r,web.StreamResponse):
            return r

        if isinstance(r,bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp

        if isinstance(r,str):
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp

        if isinstance(r,dict):
            template = r.get('__template__')
            if template is None:
                resp = web.Response(body=json.dumps(r,ensure_ascii=False,default= lambda o:o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp

            else:
                # r['__user__'] = request.__user__
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp

        if isinstance(r,int) and r >= 100 and r < 600:
            return web.Response(r)

        if isinstance(r,tuple) and len(r) == 2:
            t,m = r
            if isinstance(t,int) and t >= 100 and t < 600:
                return web.Response(t,str(m))

        # default
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response

# 将一个浮点数转换成日期字符串
def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'

    if delta < 3600:
        return u'%s分钟前' % (delta // 60)

    if delta < 86400:
        return u'%s小时前' % (delta // 3600)

    if delta < 604800:
        return u'%s天前' % (delta // 86400)

    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year,dt.month,dt.day)

@asyncio.coroutine
def init(loop):
    yield from www.orm.create_pool(loop=loop,host='127.0.0.1',port =3306,user='root',password='123456789',db='awesome')

    #  handlers: url对应的内容 middlewares：根据内容的类型决定具体返回的形式
    app = web.Application(loop=loop, middlewares=[
        logger_factory, response_factory
    ])

    # jinja2的filter（过滤器）
    init_jinja2(app, filters=dict(datetime=datetime_filter))

    add_routes(app, 'handlers')  # 与handlers.py 文件名一致
    add_static(app)

    srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9090)

    logging.info('server started at http://127.0.0.1:9090...')
    return srv

loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()

