#!/usr/bin/env.python
# -*- coding: utf-8 -*-

# Web框架设计：从使用者出发，目的让使用者便携尽可能少的代码
# 编写简单的函数而不是引入request、web.Response，可以单独测试，否则需要模拟一个request才能测试

import asyncio,os,inspect,logging,functools

from urllib import parse

from aiohttp import web

import www.apis

def get(path):
    '''
    define decorator @get('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__method__ = 'GET'
        wrapper.__route__ = path
        return wrapper
    return decorator

def post(path):
    '''
    define decorator @post('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__methond__ = 'poth'
        wrapper.__route__ = path
        return wrapper
    return decorator


# 封装一个URL处理函数
class RequestHandler(object):
    '''
    从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数，然后把结果转换为web.Response对象
    '''

    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        ...

    @asyncio.coroutine
    def __call__(self, request):
        kw = None
        r = yield from self._func(**kw)
        return r

# 用来注册一个URL处理函数
def add_route(app,fn):
    method = getattr(fn,'__method__',None)
    path = getattr(fn,'__route__',None)

    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))

    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)

    logging.info('add route %s %s => %s (%s)' % (method,path,fn.__name__,','.join(inspect.signature(fn).parameters.keys())))

    app.route.add_route(method,path,RequestHandler(app,fn))

# 自动把模块的所有符合条件的函数进行注册
def add_routes(app,module_name):
    n = module_name.rfind('.')

    # n=-1，说明module_name中不含'.'，动态加载该模块
    if n == (-1):
        mod = __import__(module_name,globals(),locals())
    else:
        '''
            例：aaa.bbb类型，需要从handle中加载blog
            n=handle长度：6
            name = blog
            mod = 动态加载handle.blog
        '''
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n],globals(),locals(),[name]),name)

    # 把所有url处理函数给注册了
    for attr in dir(mod):
        if attr.startswith('_'):
            continue

        fn = getattr(mod,attr)

        if callable(fn):
            method = getattr(fn,'__method__',None)
            path = getattr(fn,'__route__',None)
            if method and path:
                add_route(app,fn)
