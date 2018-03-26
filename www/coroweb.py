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
        @functools.wraps(func)  # functools.wraps：保留原函数信息
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
        wrapper.__methond__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

def get_required_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.kEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

def get_named_kw_args(fn):
    args = []
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def has_named_kw_args(fn):
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def has_var_kw_arg(fn):
    params = inspect.signature(fn).parameters
    for name,param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(fn):
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name,param in params.items():
        if name == 'request':
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL
                      and param.kind != inspect.Parameter.KEYWORD_ONLY
                      and param.kind != inspect.Parameter.VAR_KEYWORD ):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__,str(sig)))


# 封装一个URL处理函数
class RequestHandler(object):
    '''
    从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数，然后把结果转换为web.Response对象
    '''

    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg
        self._has_var_kw_arg = has_var_kw_arg
        self._has_named_kw_args = has_named_kw_args
        self._named_kw_args = get_named_kw_args
        self._required_kw_args = get_required_kw_args


    @asyncio.coroutine
    def __call__(self, request):
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST':
                if not request.content_type:
                    return web.HTTPBadRequest('Missing content-type.')

                ct = request.content_type.lower()
                if ct.startwith('application/json'):
                    params = yield from request.json()
                    if not isinstance(params,dict):
                        return web.HTTPBadRequest('JSON body must be object.')

                    kw = params
                elif ct.startwith('application/x-wwww-form-urlencoded') or ct.startwith('multipart/form-data'):
                    params = yield from request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest('Unsupported Content-Type： %s' % request.content_type)

            if request.method == 'GET':
                qs = request.query_string
                if qs:
                    kw = dict()
                    for k,v in parse.parse_qs(qs,True).items():
                        kw[k] = v[0]

        if kw is None:
            kw = dict(**request.match_info)
        else:
            if not self._has_var_kw_arg and self._named_kw_args:
                # remove all unamed kw
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy

                #check named arg:
                for k,v in request.match_info.items():
                    if k in kw:
                        logging.warn('Duplicate arg name in named arg and kw args: %s') % w
                    kw[k] = v

        if self._has_request_arg:
            kw['request'] = request

        #check required kw
        if self._required_kw_args:
            for name in self._required_kw_args:
                if not name in kw:
                    return web.HTTPBadRequest('Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = yield from self._func(**kw)
            return r
        except  www.apis.APIError as e:
            return dict(error=e.error,data=e.data,message=e.message)
    # __call__ 类装饰器  使用方法：@RequestHandler

def add_static(app):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
    app.route.add_static('/static/',path)
    logging.info('add static %s => %s' % ('/static/',path))

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


'''
inspect模块主要提供了四种用处：
(1). 对是否是模块，框架，函数等进行类型检查。
(2). 获取源码
(3). 获取类或函数的参数的信息
(4). 解析堆栈
'''