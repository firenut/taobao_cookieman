# -*- coding: utf-8 -*-
# TaiBao CookieMan
# by ManTianyang 2014



import sys
import os
import md5
import json
import shutil
import subprocess as shell
import threading
import datetime,time
from flask import Flask
from flask import jsonify
from flask import request
from jinja2 import Template
from jinja2 import Environment
from jinja2 import FileSystemLoader


reload(sys)
sys.setdefaultencoding( "utf-8" )

#ph = shell.Popen("casperjs --output-encoding=gbk D:/manPro/lab/login/testc.js")
#print ph


"""
HTTP METHOD
"""
GET		= 'GET'
POST	= 'POST'
PUT		= 'PUT'
DELETE 	= 'DELETE'

"""
RESPONSE STATUS
"""
RUNNING 	= 101 #运行中
UN_RUNNING	= 102 #未运行
UN_REGISTER = 103 #未注册
NO_RESULT	= 104 #运行中但是没有得到结果(这种情况需要等待)
COOKIE_NOT_FOUND = 105 #cookie未找到

ERROR_1 = 201 #请输入密码
ERROR_2 = 202 #请输入账户名
ERROR_3 = 203 #请输入验证码
ERROR_4 = 204 #验证码错误，请重新输入
ERROR_5 = 205 #该账户已被冻结，暂时无法登录
ERROR_6 = 206 #为了您的账户安全，请输入验证码
ERROR_7 = 207 #您输入的密码和账户名不匹配，请重新输入



###################################

"""
flask config
"""
app = Flask(__name__)
app.debug = True #debug模式下，可以热部署
###################################

"""
模板配置
"""
templateEnv = Environment(loader=FileSystemLoader('./template'))
login_cfg_tpl = templateEnv.get_template('login-cfg.ctp') #登录模板
login_script_tpl = templateEnv.get_template('platform_login.ctp') #登录脚本模板


"""
service context
"""

"""
 key: 店铺名(账号)
 value:
 {
	proc:句柄
 }
"""
_shops = {}

"""
{'pid':'123',proc:<obj>}
"""
_proc = {}

"""
分类所对应的shop_key
"""
_category ={}
##################################


class status_worker(threading.Thread):
	"""
		用于轮询自动登录成功或者失败
	"""
	def __init__(self,path,shop_key, delay=5):
		threading.Thread.__init__(self)
		self.shop_key = shop_key
		self.delay = delay
		self.path = path
	def run(self):
		print 'status poll running..'
		flag = True
		while flag:
			time.sleep(self.delay)
			if _shops[self.shop_key]['pid'] is None:
				flag = False

			# 读取状态文件
			status_file = self.path+'status.txt'
			if os.path.exists(status_file):
				f = open(status_file, 'r')
				status = f.readline() #success || fail
				if status == 'fail':
					f.close()
					restart_shop(self.shop_key)
					flag = False
				f.close()
			else:
				print 'file not find yet...'


def file_path(root,filename):
	return root+filename

def generate_key(*pros):
	"""
		对传入参数进行拼接并将拼接后的结果进行hash作为返回值
	"""
	source_key = ''.join(pros)
	hash = md5.new()
	hash.update(source_key)
	encode_key = hash.hexdigest()
	#TODO: log to file
	return encode_key



def write_casper_status(file,value):
	fs = open(file, 'w')
	fs.write(value)
	fs.close()

def __dump(tpl,var,filename,encode_path):
	"""
		 转储
		 return 转储文件路径
	"""

	#if path is None:
	#	path = filename
	
	#目录名转成小写md5避免中文
	#hash = md5.new()
	#hash.update(path)
	#encode_path = hash.hexdigest()

	cwd = os.getcwd()
	if os.path.exists(cwd + '\\'+encode_path):
		shutil.rmtree(cwd + '\\'+encode_path)

	os.mkdir(encode_path)
	target_path = cwd + '\\'+encode_path + '\\'

	tpl.stream(var).dump(target_path+filename,encoding='utf8')
	return target_path

def __get_shop(shop_key,attr=None):
	"""
		通过店铺名，和对应的attr得到attr的值，如果attr是None则只返回shop字典
	"""
	if shop_key in _shops:
		shop = _shops[shop_key]
		if attr is None:
			return shop
		elif attr in shop:
			return shop[attr],shop
		else:
			return None #TODO 应异常处理
	else:
		return None #TODO 应异常处理

def shop_status(shop_key):
	"""
		获得店铺当前状态
	"""
	pass

def save_or_update_shop(shop_user,shop_pwd,url,elm_u_name,elm_p_name):
	"""
		保存/更新店铺信息
		1.如果服务中有店铺则更新并保持状态，没有则新加
	"""
	print shop_user

	shop_key = generate_key(shop_user,url)

	#注册店铺信息
	#通过模板生成店铺对应的配置文件，生成目录
	tmpVar = {'shop_name':shop_user,'shop_pwd':shop_pwd,'platform_url':url,'elm_u_name':elm_u_name,'elm_p_name':elm_p_name}
	shop_root = __dump(login_cfg_tpl,tmpVar,'login-cfg.json',shop_key)

	vroot =shop_root.replace('\\','/')

	is_shop_exists = __get_shop(shop_key)
	if is_shop_exists :
		_shops[shop_key]['path'] = shop_root
		_shops[shop_key]['username'] = shop_user
		_shops[shop_key]['pwd'] = shop_pwd
		_shops[shop_key]['url'] = url

		# 如果处于运行中则 1.停止 2.更新 3.运行;
		if _shops[shop_key]['pid'] is None:
			login_script_tpl.stream({'path':vroot}).dump(shop_root+'platform_login.js',encoding='utf8')
		else:
			stop_shop(shop_key)
			login_script_tpl.stream({'path':vroot}).dump(shop_root+'platform_login.js',encoding='utf8')
			#start_shop(shop_key)
		
	else:
		login_script_tpl.stream({'path':vroot}).dump(shop_root+'platform_login.js',encoding='utf8')
		_shops[shop_key] = {}
		_shops[shop_key]['pid'] = None
		_shops[shop_key]['path'] = shop_root
		_shops[shop_key]['username'] = shop_user
		_shops[shop_key]['pwd'] = shop_pwd
		_shops[shop_key]['url'] = url

	return shop_key





	

def start_shop(shop_key,is_poll):
	"""
		启动店铺服务
	"""
	print shop_key
	if shop_key not in _shops :
		return 'fail',UN_REGISTER

	if _shops[shop_key]['pid'] is not None:
		return 'fail',UN_RUNNING

	#将登录脚本拷贝到对应目录
	target_path = _shops[shop_key]['path']

	#shutil.copy('./platform_login.js',target_path) #target_path

	#生成对应启动命令
	poll_arg = "--poll=false"
	if is_poll:
		poll_arg = "--poll=true"
	start_command = 'casperjs --output-encoding=gbk %splatform_login.js %s ' % (target_path,poll_arg)

	#生成控制脚本状态文件
	#TODO: 将状态值常量化
	#write_casper_status(file_path(target_path,'casper_run_status.txt'),'1')
	print start_command
	ph = shell.Popen(start_command)
	_shops[shop_key]['pid'] = ph.pid
	_proc[shop_key] = ph

	print '*'*20
	print 'start ' ,shop_key,ph.pid
	print '*'*20

	#启动该店铺的状态轮询线程
	if is_poll:
		worker = status_worker(target_path,shop_key)
		worker.start()

	return 'success',_shops[shop_key]['pid']

	

def stop_shop(shop_key):
	"""
		停止店铺服务
	"""

	#proc = _proc[shop_key]
	#proc.terminate()
	#write_casper_status(file_path(_shops[shop_key]['path'],'casper_run_status.txt'),'0')
	if shop_key in _shops:
		casper_pid = _shops[shop_key]['pid']

		_shops[shop_key]['pid'] = None
		os.system("taskkill  /f /t /pid %s" % casper_pid)
		path = _shops[shop_key]['path']
		if os.path.exists(path + 'cookies.txt'):
			os.remove(path + 'cookies.txt')
		
		if os.path.exists(path + 'status.txt'):
			os.remove(path + 'status.txt')
		return casper_pid

def restart_shop(shop_key):
	"""
		重启店铺服务
	"""
	stop_shop(shop_key)
	status = start_shop(shop_key,True)
	return status



def remove_shop(shop_key):
	"""
		删除店铺
		1.停止店铺服务
		2.删除店铺信息
	"""
	stop_shop(shop_key)
	del _shops[shop_key]

def shop_path(*path):
	return '/shop/'+'/'.join(path)

def build_resp(state,data):
	resp = {'state':state,'data':data}
	return jsonify(resp)

def __exec(wait=True):
	pass

class TaobaoLoginAPI():
	@app.errorhandler(404)
	def page_not_found(error):
		return 'This interface does not exist', 404
	
	@app.route(shop_path('<string:category>','status'),methods=[GET])
	def shop_status(category):
		"""
			查询店铺状态
		"""
		if category in _category:
			shop_key = _category[category]
			if shop_key not in _shops:
				return build_resp('fail',UN_REGISTER)
			elif _shops[shop_key]['pid'] is None:
				return build_resp('fail',UN_RUNNING)
			
			return build_resp('success',RUNNING)
		else:
			return build_resp('fail',UN_REGISTER)

		

	@app.route(shop_path('<string:category>'),methods=[POST])
	def reg_or_update_shop(category):
		"""
			注册/更新 店铺
			如果上下文中没有输入店铺则注册否则，先删除原有店铺信息，
			然后加入新店铺并保持原店铺的运行状态
		"""
		username = request.form['username']
		password = request.form['pwd']
		url = request.form['url']
		#elm_u_name = request.form['user_elm_id']
		#elm_p_name = request.form['pwd_elm_id']
		#print 'url' in request.form
		#elmUId = request.form['elmUId']
		#elmPId = request.form['elmPId']
		#print elmUId


		elm_u_name = 'TPL_username'
		elm_p_name = 'TPL_password'
		if 'user_elm_id' in request.form and 'pwd_elm_id' in request.form:
			elm_u_name = request.form['user_elm_name']
			elm_p_name =  request.form['pwd_elm_name']

		shop_key = save_or_update_shop(username,password,url,elm_u_name,elm_p_name)
		_category[category] = shop_key
		return build_resp('success',shop_key)

	@app.route(shop_path('<string:category>'),methods=[DELETE])
	def del_shop(category):
		"""
			删除店铺
		"""
		if category in _category:
			shop_key = _category[category]
			remove_shop(shop_key)
			return build_resp('success',shop_key)
		else:
			return build_resp('fail',UN_REGISTER)

	@app.route(shop_path('<string:category>','start'))
	def start_shop(category):
		"""
			开始获取已注册店铺信息
		"""
		if category in _category:
			shop_key = _category[category]
			status = start_shop(shop_key,True)
			return build_resp(status[0],status[1])
		else:
			return build_resp('fail',UN_REGISTER)

	@app.route(shop_path('<string:category>','once'))
	def start_shop_once(category):
		"""
			开始获取已注册店铺信息
		"""
		if category in _category:
			shop_key = _category[category]
			status = start_shop(shop_key,False)
			if category in _category:
				shop_key = _category[category]
				if shop_key not in _shops:
					return build_resp('fail',UN_REGISTER)

				path = _shops[shop_key]['path']+'cookies.txt'
				flag = True
				while flag:
					time.sleep(5)
					if os.path.exists(path):
						cookie_file = open(path,'r')
						cookie_str = cookie_file.read()
						decodejson = json.loads(cookie_str)
						cookie_file.close()
						flag = False
						return build_resp('success',decodejson)
			else:
				return build_resp('fail',UN_REGISTER)		
			
		else:
			return build_resp('fail',UN_REGISTER)

	@app.route(shop_path('<string:category>','stop'))
	def stop_shop(category):
		"""
			停止获取已注册的店铺信息
		"""
		if category in _category:
			shop_key = _category[category]
			pid = stop_shop(shop_key)
			return build_resp('success',pid)
		else:
			return build_resp('fail',UN_REGISTER)

	@app.route(shop_path('<string:category>','restart'))
	def restart_shop(category):
		"""
			重启服务
		"""
		if category in _category:
			shop_key = _category[category]
			status = restart_shop(shop_key)
			return build_resp(status[0],status[1])
		else:
			return build_resp('fail',UN_REGISTER)

	
	@app.route(shop_path('<string:category>','cookies'))
	def shop_cookies(category):
		"""
			得到对应店铺的cookie
		"""
		if category in _category:
			shop_key = _category[category]
			if shop_key not in _shops:
				return build_resp('fail',UN_REGISTER)

			path = _shops[shop_key]['path']+'cookies.txt'

			if os.path.exists(path):
				cookie_file = open(path,'r')
				cookie_str = cookie_file.read()
				decodejson = json.loads(cookie_str)
				cookie_file.close()
				return build_resp('success',decodejson)
			elif _shops[shop_key]['pid'] is not None:
				return build_resp('fail',NO_RESULT)
			else:
				return build_resp('fail',UN_RUNNING)
		else:
			return build_resp('fail',UN_REGISTER)


	@app.route(shop_path('<string:category>','cookie','<string:name>'))
	def shop_cookies_by_category(category,name):
		"""
			得到对应店铺的cookie by key
		"""
		if category in _category:
			shop_key = _category[category]
			if shop_key not in _shops:
				return build_resp('fail',UN_REGISTER)

			path = _shops[shop_key]['path']+'cookies.txt'
			
			print path

			if os.path.exists(path):
				cookie_file = open(path,'r')
				cookie_str = cookie_file.read()
				decodejson = json.loads(cookie_str)
				print '-'*50
				print cookie_str
				print '-'*50
				cookie_file.close()
				if name in decodejson:
					return build_resp('success',decodejson[name])
				else:
					return build_resp('fail',COOKIE_NOT_FOUND)
			elif _shops[shop_key]['pid'] is not None:
				return build_resp('fail',NO_RESULT)
			else:
				return build_resp('fail',UN_RUNNING)
		else:
			return build_resp('fail',UN_REGISTER)
		
		

	@app.route(shop_path('list'),methods=[GET])
	def list_shop():
		"""
			列出所有店铺信息
		"""
		
		infos = {}

		for category in _category:
			shop = _shops[_category[category]]
			print shop
			infos[category] = {}
			infos[category]['key'] = _category[category]
			infos[category]['username'] = shop['username']
			infos[category]['pwd'] = shop['pwd']
			infos[category]['url'] = shop['url']
			infos[category]['pid'] = shop['pid']

		return json.dumps(infos,ensure_ascii=False)


if __name__ == '__main__':
	#register_api(TaobaoLoginAPI,'taobao_login_api','/taobao/')
	app.run(port=9080,host="0.0.0.0")