taobao_cookieman
================

定时登陆淘宝获取有效cookie，用于爬虫请求淘宝相应数据平台

### 文件：
**login_robot.py**

- 提供Restful服务

**template/login-cfg.ctp**

- 配置模板基本不用更改

**template/platform_login.ctp**

- 爬虫脚本模板，通过配置后生成 `${店铺名}_login.js` 爬虫文件


### 依赖：

1. python 2.6+
2. casperJs 1.0+


*注意：casperJs 依赖 PhantomJS 1.8.2 以上版本*

### 配置：

服务入口： `login_robot.py` 

缺省端口： `9080`


### 使用:

具体API请查看 class `TaobaoLoginAPI`(): 中的请求方法 `已注释`


### 基本流程：
template 
	-. 