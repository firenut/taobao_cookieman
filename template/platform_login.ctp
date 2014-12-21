////////////build in///////////////////////////
var fs = require('fs');
var utils = require('utils');

var cfg = (function _loadConfig(){
	var stream = fs.open('{{path}}login-cfg.json','r');
	var data = JSON.parse(stream.read());
	stream.close();
	return data;
})();

var casper = require('casper').create({
	logLevel:cfg['log']['logLevel'],
	verbose:cfg['log']['verbose']
	
});
var cli = casper.cli;
//phantom.outputEncoding = cfg['encode'];
casper.userAgent(cfg['userAgent']);

//casper.options.pageSettings.loadImages = true;
casper.options.viewportSize = {'width': 1024, 'height': 768};
////////////////////////////////////////////

var poll = false;
if(cli.get("poll")){
	poll = true;
}

//用于通知中心
var buzzer = function _buzzer(){
}


var life_control = function _life_control(){
	var exists = fs.exists('{{path}}casper_run_status.txt');

	if(exists){
		var content = fs.read('{{path}}casper_run_status.txt');
		casper.log('----------------------------->>>>>> '+content)
		if(content == 0){
			casper.exit();
		}	
	}

    setTimeout(life_control,5000)

}


//把cooike整理成 key(name)/value 的形式
var fomart_cookie = function _fomart_cookie(cookies){
	var sources = phantom.cookies;//object[{}...]
	var len = sources.length;
	var target = {};
	while(len--){
		target[sources[len]['name']] = sources[len]['value'];
	}

	return JSON.stringify(target);

}

var getCooikeValueByName = function _getCooikeValueByName(name,cookies){
	var i = cookies.length;
	var result = null;
	while(i--){
		if(cookies[i]['name'] === name){
			result = cookies[i]['value'];
			break;
		}
	}
	return result;
}

///////////flow/////////////////////////
casper.start(function(response){
	//phantom.clearCookies();
	//casper.clear();
});

casper.thenOpen(cfg['login']['url'],function(response){
	this.log(JSON.stringify(response),'debug');
	if(response.status !== 200){
		this.log(response.status,'info');
		this.log(cfg['login']['url'],'info');
		//TODO: 报警
	}else{
		this.log('Connect : '+ this.getTitle() + ' Successful','info');
	}
});


casper.then(function(){
	casper.wait(10000, function() {
		this.log('wait 10 sec.','debug');
	});
})
//////////////////////////////////////////////////////
////	登录页面操作	
//////////////////////////////////////////////////////

//切换到表单context
casper.then(function(response){
	this.log("URL: " + this.getCurrentUrl() ,'debug')
	this.page.switchToChildFrame(0);

	// casper.wait(3000, function() {
	// 	this.log('wait 3 sec.','debug');
	// });
	//TODO:模拟鼠标操作
});


//DOM操作：填入用户名密码
casper.thenEvaluate(function(username,password,elm_u_name,elm_p_name){
	//document.querySelector('.ph-label').setAttrisbute('class','.ph-hide .ph-label');
	document.querySelector('#J_StaticForm input[name="'+elm_u_name+'"]').value=username;
	document.querySelector('#J_StaticForm input[name="'+elm_p_name+'"]').value=password;
	
},cfg['login']['username'],cfg['login']['password'],cfg['login']['elm_u_name'],cfg['login']['elm_p_name']);


casper.wait(3000, function() {
	this.log('wait 3 sec.','debug');
});

casper.then(function(){
	this.capture("{{path}}pre-login.png");
});

//提交表单
casper.then(function(response){
	//alert('---> '+document.querySelector('#J_StaticForm input[name="TPL_username"]').value);
	// this.log('---> '+document.querySelector('#J_StaticForm input[name="TPL_password"]').value,'debug');
	this.mouseEvent('click', '#J_StaticForm #J_SubmitStatic');
	//this.page.switchToMainFrame();
	//TODO:模拟鼠标操作
});

casper.waitFor(function(){
	//headlist: 魔方登录成功标记，jifen-mod: 量子登录成功标记
	var flag =  this.evaluate(function() {
		return window.parent.frames.length == 0;
		//return document.querySelectorAll("#headlist").length > 0 || document.querySelectorAll("#jifen-mod").length > 0 ;
	});
	this.log('验证登录状态--> ' + flag ,'debug');
	return flag;
},function then(){
	this.log('登录成功!','info');
	this.page.switchToMainFrame();

	this.capture("{{path}}success_screen.png");
	

	fs.write('{{path}}cookies.txt', fomart_cookie(phantom.cookies), 'w');

	var flag =  this.evaluate(function() {
		return window.frames.length == 0;
		//return document.querySelectorAll("#headlist").length > 0 || document.querySelectorAll("#jifen-mod").length > 0 ;
	});

	if(flag){
		fs.write('{{path}}status.txt', 'success', 'w');
	}else{
		fs.write('{{path}}status.txt', 'fail', 'w');
		casper.exit();
	}
	if(poll){
		this.repeat(98000, function() {
			
			this.capture("{{path}}success_screen.png");
			

			fs.write('{{path}}cookies.txt', fomart_cookie(phantom.cookies), 'w');

			var flag =  this.evaluate(function() {
				return window.frames.length == 0;
				//return document.querySelectorAll("#headlist").length > 0 || document.querySelectorAll("#jifen-mod").length > 0 ;
			});

			if(flag){
				fs.write('{{path}}status.txt', 'success', 'w');
			}else{
				fs.write('{{path}}status.txt', 'fail', 'w');
				casper.exit();
			}


			casper.wait((3*60*1000),function(){
				this.log('reloaded...','debug');
				/*
				var exists = fs.exists('{{path}}casper_run_status.txt');

				if(exists){
					var content = fs.read('{{path}}casper_run_status.txt');
					casper.log('----------------------------->>>>>> '+content)
					if(content == 0){
						casper.exit();
					}	
				}*/

				this.reload();
			})
		});
	}

	//utils.dump(phantom.cookies)
	

},function timeOut(){
	var error_msg = this.evaluate(function() {
		//console.log(document.body.innerHTML);
		return document.querySelector("#J_Message p").innerHTML.split("。")[0];
	});

	this.log('登录失败: '+error_msg ,'info');
	this.capture("{{path}}fail_screen.png");
	fs.write('{{path}}status.txt','fail', 'w');
  	casper.exit();

},10000);



casper.run();

