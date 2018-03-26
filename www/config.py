#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
    简化读取配置文件，把所有配置读取到统一的文件中。
'''
from www import config_default

class Dict(dict):
    '''
    Simple dict but support access as x.y style
    '''

    def __init__(self,names=(),values=(),**kw):
        super(Dict,self).__init__(**kw)
        for k,v in zip(names,values):
            self[k] = v

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Dict' object has no attribute '%s'" % key)

def merge(defaults,override):
    r = {}
    for k,v in defaults.items():
        if k in override:
            if isinstance(v,dict):
                r[k] = merge(v,override)
            else:
                r[k] = override[k]
        else:
            r[k] = v

    return r

def toDict(d):
    D = Dict()
    for k,v in d.items():
        D[k] = toDict(v) if isinstance(v,dict) else v

    return D

configs = config_default.configs

# 将开发环境、生产环境的配置进行合并
try:
    import  www.config_override
    configs = merge(configs,www.config_override.configs)
except ImportError:
    pass

configs = toDict(configs)