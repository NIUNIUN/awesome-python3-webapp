#!/usr/bin/env.python
# -*- coding: utf-8 -*-

import logging
import asyncio
import aiomysql

#创建连接池
'''
全局连接池：每个HTTP请求直接从连接池中获取数据库连接。
使用连接池的好处是不必频繁地打开和关闭数据库连接，而是能复用就尽量复用。
'''

def log(sql,args=()):
    logging.info('SQL: %s' % sql)

@asyncio.coroutine
def create_pool(loop,**kw):
    logging.info('CREATE DATABASE connection pool...')
    global __pool   #全局变量，存储连接池
    __pool = yield from aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['user'],
        password=kw['password'],
        db=kw['db'],
        charset=kw.get('charset', 'utf8'),   # 默认编码格式：utf-8
        autocommit=kw.get('autocommit', True),  # 自动提交事务
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop = loop
    )

@asyncio.coroutine
def select(sql,args,size = None):
    log(sql,args)
    global __pool
    with (yield from __pool) as conn:
        cur = yield from conn.cursor(aiomysql.DictCursor)
        yield from cur.execute(sql.replace('?','%s'),args or())  #SQL占位符：？，MySQL的占位符：%s。坚持使用带参数的SQL，而不是自己拼接SQL字符串，防止SQL注入攻击
        if size:
            rs = yield from cur.fetchmany(size)  # 通过fetchmany()获取最多指定数量的记录
        else:
            rs = yield  from cur.fetchmany()   # 获取所有记录
        yield from cur.close()
        logging.info('rows returned: %s' % len(rs))
        return rs   #返回结果集

# 执行insert、update、delete语句
@asyncio.coroutine
def execute(sql,args):
    log(sql)
    with (yield from __pool) as conn:
        try:
            cur = yield from conn.cursor()
            yield from cur.execute(sql.replace('?','%s'),args)
            affected = cur.rowcount  # 受影响行数
            yield from cur.close()
        except BaseException as e:
            raise
    return affected

def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
    return ','.join(L)

# 将Model的具体子类的映射信息读取出来
class ModelMetaclass(type):
    def __new__(cls,name,bases,attrs):
        if name == 'Model':
            return  type.__new__(cls,name,bases,attrs)
        # 获取table名称
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))

        # 获取所有的Field和主键名
        mappings = dict()
        fields = []
        primaryKey = None
        for k,v, in attrs.items():
            if isinstance(v,Field):
                logging.info('found mapping: %s ==> %s' %(k,v))
                mappings[k] = v
                if v.primary_key:
                    if primaryKey:
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey:
            raise  RuntimeError('Primary key not found.')
        for k in mappings.keys():
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings  # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey  # 主键属性名
        attrs['__fields__'] = fields  # 除主键外的属性名
        # 构造默认的SELECT, INSERT, UPDATE和DELETE语句:
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (
        tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (
        tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

# 定义Model：所有ORM映射的基类
# 继承dict，具备所有dict的功能，同时实现了特殊方法__getattr__()和__setattr__()，又可以引用普通字段
# 任何继承Model的类，会自动通过ModelMetaclass扫描映射关系，并存储到自身的类属性（如__table__、__mapping__）中
class Model(dict,metaclass=ModelMetaclass):
    def __int__(self,**kw):
        super(Model,self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self,key):
        return getattr(self,key,None)

    def getValueOrDefault(self,key):
        value = getattr(self,key,None)
        if value is None:
            field = self.__mappings__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key,str(value)))
                setattr(self,key,value)
        return value

    # 添加class方法，让所有子类调用class方法   （类似于static方法）
    @classmethod
    @asyncio.coroutine
    def find(cls,pk):
        'find object by primary key.'
        rs = yield from select('%s where `%s`=?' % (cls.__select__,cls.__primary_key__),[pk],1)
        if len(rs)==0:
            return None
        return cls(**rs[0])

    @classmethod
    @asyncio.coroutine
    def findAll(cls,where=None,args= None,**kw):
        'find object by where calsus.'
        sql = [cls.__select__]
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:
            args = []

        orderBy = kw.get('orderBy',None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)

        limit = kw.get('limit',None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit,int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit,tuple) and len(limit) ==2:
                sql.append('?,?')
                args.extend(limit)
            else:
                raise  ValueError('Invalid limit value: %s' % str(limit))

        rs = yield  from  select(' '.join(sql),args)
        return [cls(**r) for r in rs]

    @classmethod
    @asyncio.coroutine
    def findNumber(cls,selectField,where= None,args = None):
        'find number by select and where.'
        sql = ['select % _num_from `%s`' % (selectField,cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)

        rs = yield from select(' '.join(sql),args,1)
        if len(rs) == 0:
            return  None
        return rs[0]['_num_']

    # 实例方法
    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueOrDefault,self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__insert__,args)
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    @asyncio.coroutine
    def update(self):
        args = list(map(self.getValue,self.__fields__))
        args.append(self.getValue(self.__primary_key__))
        rows = yield from execute(self.__update__,args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    @asyncio.coroutine
    def remove(self):
        args = [self.getValue(self.__primary_key__)]
        rows = yield from execute(self.__delete__,args)
        if rows != 1:
            logging.warn('failed to remove by primary key : affected rows: %s' % rows)


class Field(object):
    def __init__(self,name,column_type,primary_key,default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        return '<%s,%s:%s>' % (self.__class__.__name__,self.column_type,self.name)

class StringField(Field):
    def __init__(self,name=None,primary_key= False,default=None,ddl = 'varchar(100)'):
        super().__init__(name,ddl,primary_key,default)

class BooleanField(Field):
    def __init__(self,name=None, default=False):
        super().__init__(name,'boolean',False,default)

class IntegerField(Field):
    def __init__(self,name=None,primary_key=False,default=0):
        super().__init__(name,'bigint',primary_key,default)

class FloatField(Field):
    def __init__(self,name=None,primary_key=False,default=0.0):
        super().__init__(name,'real',primary_key,default)

class TextField(Field):
    def __init__(self,name=None,default=None):
        super().__init__(name,'text',False,default)

