#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
    配置文件
    开发环境的标准配置
'''

configs = {
    'debug':True,
    'db':{
        'host':'127.0.0.1',
        'port':3306,
        'user':'root',
        'password':'123456789',
        'database':'awesome'
    },
    'session':{
        'secret':'Awesome'
    }
}