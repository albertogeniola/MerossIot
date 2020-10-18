Search.setIndex({docnames:["advanced-topics","api-reference/controller/device/base","api-reference/controller/device/channel","api-reference/controller/device/generic","api-reference/controller/device/hub","api-reference/controller/mixins/consumption","api-reference/controller/mixins/electricity","api-reference/controller/mixins/garage","api-reference/controller/mixins/hub","api-reference/controller/mixins/light","api-reference/controller/mixins/spray","api-reference/controller/mixins/system","api-reference/controller/mixins/toggle","api-reference/controller/subdevice/sensor","api-reference/controller/subdevice/valve","api-reference/http","api-reference/index","api-reference/manager","common-gotchas","index","installation","meross-arch","meross-protocol","quick-start"],envversion:{"sphinx.domains.c":1,"sphinx.domains.changeset":1,"sphinx.domains.citation":1,"sphinx.domains.cpp":1,"sphinx.domains.index":1,"sphinx.domains.javascript":1,"sphinx.domains.math":2,"sphinx.domains.python":1,"sphinx.domains.rst":1,"sphinx.domains.std":1,sphinx:56},filenames:["advanced-topics.rst","api-reference/controller/device/base.rst","api-reference/controller/device/channel.rst","api-reference/controller/device/generic.rst","api-reference/controller/device/hub.rst","api-reference/controller/mixins/consumption.rst","api-reference/controller/mixins/electricity.rst","api-reference/controller/mixins/garage.rst","api-reference/controller/mixins/hub.rst","api-reference/controller/mixins/light.rst","api-reference/controller/mixins/spray.rst","api-reference/controller/mixins/system.rst","api-reference/controller/mixins/toggle.rst","api-reference/controller/subdevice/sensor.rst","api-reference/controller/subdevice/valve.rst","api-reference/http.rst","api-reference/index.rst","api-reference/manager.rst","common-gotchas.rst","index.rst","installation.rst","meross-arch.rst","meross-protocol.rst","quick-start.rst"],objects:{"meross_iot.controller.device":{BaseDevice:[1,0,1,""],ChannelInfo:[2,0,1,""],GenericSubDevice:[3,0,1,""],HubDevice:[4,0,1,""]},"meross_iot.controller.device.BaseDevice":{async_update:[1,1,1,""],channels:[1,1,1,""],firmware_version:[1,1,1,""],hardware_version:[1,1,1,""],internal_id:[1,1,1,""],lookup_channel:[1,1,1,""],name:[1,1,1,""],online_status:[1,1,1,""],register_push_notification_handler_coroutine:[1,1,1,""],type:[1,1,1,""],unregister_push_notification_handler_coroutine:[1,1,1,""],uuid:[1,1,1,""]},"meross_iot.controller.device.GenericSubDevice":{async_get_battery_life:[3,1,1,""],async_update:[3,1,1,""],internal_id:[3,1,1,""],online_status:[3,1,1,""]},"meross_iot.controller.mixins.consumption":{ConsumptionXMixin:[5,0,1,""]},"meross_iot.controller.mixins.consumption.ConsumptionXMixin":{async_get_daily_power_consumption:[5,1,1,""]},"meross_iot.controller.mixins.electricity":{ElectricityMixin:[6,0,1,""]},"meross_iot.controller.mixins.electricity.ElectricityMixin":{async_get_instant_metrics:[6,1,1,""],get_last_sample:[6,1,1,""]},"meross_iot.controller.mixins.garage":{GarageOpenerMixin:[7,0,1,""]},"meross_iot.controller.mixins.garage.GarageOpenerMixin":{async_close:[7,1,1,""],async_open:[7,1,1,""],get_is_open:[7,1,1,""]},"meross_iot.controller.mixins.hub":{HubMixn:[8,0,1,""],HubMts100Mixin:[8,0,1,""]},"meross_iot.controller.mixins.light":{LightMixin:[9,0,1,""]},"meross_iot.controller.mixins.light.LightMixin":{async_set_light_color:[9,1,1,""],get_color_temperature:[9,1,1,""],get_light_is_on:[9,1,1,""],get_luminance:[9,1,1,""],get_rgb_color:[9,1,1,""],get_supports_luminance:[9,1,1,""],get_supports_rgb:[9,1,1,""],get_supports_temperature:[9,1,1,""]},"meross_iot.controller.mixins.spray":{SprayMixin:[10,0,1,""]},"meross_iot.controller.mixins.system":{SystemAllMixin:[11,0,1,""],SystemOnlineMixin:[11,0,1,""]},"meross_iot.controller.mixins.toggle":{ToggleMixin:[12,0,1,""],ToggleXMixin:[12,0,1,""]},"meross_iot.controller.mixins.toggle.ToggleXMixin":{async_toggle:[12,1,1,""],async_turn_off:[12,1,1,""],async_turn_on:[12,1,1,""],is_on:[12,1,1,""]},"meross_iot.controller.subdevice":{Ms100Sensor:[13,0,1,""],Mts100v3Valve:[14,0,1,""]},"meross_iot.controller.subdevice.Ms100Sensor":{last_sampled_humidity:[13,1,1,""],last_sampled_temperature:[13,1,1,""],last_sampled_time:[13,1,1,""],max_supported_temperature:[13,1,1,""],min_supported_temperature:[13,1,1,""]},"meross_iot.controller.subdevice.Mts100v3Valve":{async_get_temperature:[14,1,1,""],async_set_preset_temperature:[14,1,1,""],get_preset_temperature:[14,1,1,""],get_supported_presets:[14,1,1,""],last_sampled_temperature:[14,1,1,""],last_sampled_time:[14,1,1,""]}},objnames:{"0":["py","class","Python class"],"1":["py","method","Python method"]},objtypes:{"0":"py:class","1":"py:method"},terms:{"3rd":19,"8bit":9,"case":[0,18,19,22,23],"class":[1,2,3,4,5,6,7,8,9,10,11,12,13,14,18,23],"default":[0,6,7,9,12,22],"enum":[1,23],"float":[13,14],"function":[0,1,13,23],"import":[19,22,23],"int":[1,2,7,9],"new":[0,18,22,23],"return":[1,3,5,6,7,9,12,13,14],"static":14,"switch":[1,12,19],"true":[7,9,12],"try":[1,3,22],"while":18,AWS:22,DNS:22,For:[0,18,19,23],Its:1,TLS:22,The:[0,6,7,13,18,19,22,23],Then:23,There:[18,22],__main__:23,__name__:23,__onoff:9,_md5:22,abl:22,about:[18,19,22,23],abov:[0,22],absolv:23,abus:18,access:[18,22,23],account:[0,18,22,23],accur:6,accuraci:22,acquir:18,actual:18,actuat:23,add:[0,18],added:0,address:[18,22],adopt:18,advanc:19,advis:0,after:[18,23],again:[18,23],against:[0,18,22],aim:22,albertogeniola:20,alert:13,align:18,all:[0,22,23],allow:[1,22,23],also:[0,22],altern:0,alwai:[0,18],ambient:23,ambient_temperatur:23,among:22,ani:[0,1,6,18,19,22],anoth:22,api:[18,19,22,23],app:[0,18,19],app_id:22,appli:18,applianc:22,applic:22,approach:[18,19],architectur:19,archiv:20,arg:[1,3,5,6,7,9,12,14],argument:23,aris:0,around:23,ask:[18,22],assign:1,assum:22,async:[1,3,5,6,7,9,12,14,19,23],async_clos:7,async_device_discoveri:23,async_from_user_password:23,async_get_battery_lif:3,async_get_daily_power_consumpt:5,async_get_instant_metr:[6,23],async_get_temperatur:14,async_init:23,async_logout:23,async_open:7,async_set_light_color:[9,23],async_set_preset_temperatur:14,async_toggl:12,async_turn_off:[12,23],async_turn_on:[12,23],async_upd:[1,3,13,18,23],asynchron:18,asyncio:[18,19,23],attack:22,attempt:22,attribut:6,author:[22,23],autom:[18,19],automat:[0,1,3,18],avail:[13,14,22,23],avoid:[6,18,23],await:[1,18,23],awar:18,backend:19,ban:[0,18],bandwidth:[1,3],base64:22,base64_encoded_password:22,base64_encoded_ssid:22,base:0,basedevic:[16,19],basic:[0,1,3,19,22,23],batteri:3,batteryinfo:3,becom:18,been:[0,1,13,14,22,23],befor:[0,18,22,23],below:0,between:[19,22,23],bind:22,bit:[0,19,23],block:[18,19],blue:9,bodi:22,bool:[2,7,9,12],both:[0,23],bought:19,bright:9,broadcast:22,broker:[0,18,19,22],bucket:0,build:[0,19,22],built:19,bulb:[9,12,19],burst:0,burst_rat:0,burst_requests_per_second_limit:0,button:[22,23],cach:[6,14,23],calcul:[6,22],call:[6,13,18],callabl:1,can:[0,1,9,13,18,20,22,23],capabl:[9,13,23],carefulli:23,carri:22,caus:18,celsiu:[13,14],certif:22,chang:[0,1,18,19,23],channel:[1,5,6,7,9,12,23],channel_id_or_nam:1,channel_typ:2,channelinfo:[16,19],character:1,check:[0,22,23],choos:23,chose:23,chosen:23,client:[16,19,23],clone:20,close:[7,18,23],cloud:[0,1,3,18,22],code:[20,23],collect:0,color:[9,23],color_temperatur:9,com:20,combin:6,command:[0,7,9,18,19,20,23],common:[19,22],commun:22,complet:[18,23],compos:[1,3],concaten:22,config:22,configur:[9,14,18,22,23],connect:[18,22,23],consent:22,conserv:18,consid:19,consumpt:[5,6,23],consumptionxmixin:[16,19,23],contact:18,contain:9,content:22,continu:0,contrari:23,control:[1,2,3,4,5,6,7,8,9,10,11,12,13,14,19],conveni:18,copi:22,core:23,coro:1,coroutin:1,could:18,creat:[0,23],credenti:[0,22],current:[0,1,3,6,7,9,14,18,23],current_color:23,danger:23,data:[1,3,5,6,13,19,23],datetim:[13,14],decid:0,dedic:0,def:23,defin:1,degre:[13,14],delai:0,deliv:[1,18],demo:23,describ:6,descript:0,design:0,detail:23,dev:23,develop:[0,1,18,19,22,23],devic:[1,2,3,4,5,6,9,12,13,14,18,19],device_class:23,device_internal_id:1,device_typ:23,device_uuid:[1,4,5,6,7,8,9,10,11,12,22],devid:0,dhcp:22,dict:[1,5],did:19,differ:[18,22,23],digest:22,digit:22,directori:0,dirti:23,disconnect:18,discov:[0,18,23],discrimin:22,document:[18,23],doe:[0,18,19,22,23],domest:22,domot:19,done:0,door:[7,19],down:23,download:20,drop:0,drope:0,due:1,each:[0,9,18],easi:0,edg:18,effort:23,electr:[6,23],electricitymixin:[16,19,23],els:[18,23],email:[18,23],embed:[1,3],enabl:9,end:18,endpoint:18,engin:22,enough:[6,22],ensur:23,enter:0,entir:23,enumer:18,environ:23,equip:23,error:18,even:[0,19,23],event:[1,18,22],everi:[18,22],exampl:23,exchang:0,exclus:23,execut:22,expect:22,experienc:18,explain:18,explicit:22,explicitli:[19,22],expos:[0,1,13,23],fact:[0,23],fals:[2,7,9,12],far:19,fast:23,featur:0,fetch:18,file:0,filter:[22,23],find:23,find_devic:23,firmwar:[1,22],firmware_vers:1,first:[0,18,19,22,23],flaw:22,flood:[0,6],flow:19,folder:0,follow:[0,20,22,23],forbidden:22,forc:[1,3,13,23],form:22,forward:23,found:23,framework:19,from:[0,5,6,9,18,20,22,23],full:[1,3,13],further:19,garag:[7,19],garageopenermixin:[16,19,23],gatewai:22,gather:[0,6],gener:[0,1,9,22,23],genericsubdevic:[16,19],get:[1,3,9,23],get_color_temperatur:9,get_event_loop:23,get_is_open:7,get_last_sampl:6,get_light_is_on:9,get_lumin:9,get_preset_temperatur:14,get_rgb_color:[9,23],get_supported_preset:14,get_supports_lumin:9,get_supports_rgb:[9,23],get_supports_temperatur:9,git:20,github:[0,20],given:[7,9,14],global:0,goe:23,going:19,gotcha:[19,23],grade:13,green:9,guarante:22,gui:19,hand:23,handl:[18,23],handler:1,happen:[18,19,22],happi:19,hard:19,hardwar:[1,19,22],hardware_vers:1,has:[0,13,14,18,22,23],have:[0,1,9,19,20,22,23],header:22,heat:23,here:23,hex:22,him:18,histor:5,hit:18,hoc:0,hold:22,host:22,hostnam:22,hour:[18,22],how:[18,19,23],howev:[0,18,22,23],http:[16,19,20,22,23],http_api:23,http_api_cli:23,http_client:23,hub:[3,8],hubdevic:[16,19],hubdevice_uuid:[3,13,14],hubmixn:[16,19],hubmts100mixin:[16,19],humid:[13,23],identifi:[1,3,22],ignor:9,imag:22,immedi:23,immin:18,implement:[0,12,18,23],inconsist:18,index:[1,2,12,19],info:[0,6,9,14],inform:[0,1,6,22,23],input:22,inspect:19,instal:19,instanc:18,instant:6,instant_consumpt:23,instead:[6,14,23],instruct:22,integ:9,intens:9,interest:[0,12],interfac:23,intern:[1,3],internal_id:[1,3],internet:18,introduc:18,invok:[1,3,18,23],iot:20,is_heat:23,is_master_channel:2,is_on:[12,23],is_open:23,isoformat:23,issu:[0,20,23],iter:14,its:[0,3,22],itself:22,json:22,keep:18,kei:22,keyword:18,kind:22,know:[19,23],known:18,kwarg:[1,3,4,5,6,7,8,9,10,11,12,13,14],last_sampled_humid:[13,23],last_sampled_temperatur:[13,14,23],last_sampled_tim:[13,14,23],latest:[13,14,20,23],least:9,len:23,let:[19,23],level:0,leverag:19,librari:[0,1,3,18,20,22,23],light:[9,23],lightmixin:[16,19,23],like:23,limit:[1,3,18,19],limit_hit:0,line:18,list:[1,5,19],listen:[0,18],liter:22,local:22,log:[0,18,22],login:22,logout:[18,23],look:[1,19,23],lookup_channel:1,loop:[18,23],loos:18,lost:18,low:0,lower:22,lumin:[9,23],mac:22,machin:18,magnet:23,mai:[0,6,18,22],main:23,make:[0,18,20,22],malici:22,manag:[1,3,4,5,6,7,8,9,10,11,12,13,14,18,19,23],mani:[18,22],manual:[20,23],map:13,mark:23,market:0,master:1,match:22,matter:0,max:23,max_supported_temperatur:[13,23],maximum:[0,13],md5:22,meant:19,measur:6,meross:[0,1,3,18,19,20,23],meross_:22,meross_devic:23,meross_email:23,meross_iot:[1,2,3,4,5,6,7,8,9,10,11,12,13,14,23],meross_password:23,meross_sniff:0,merosshttpcli:[18,23],merossiot:[0,20],merossmanag:[0,16,18,19,23],merosssnif:0,messag:[0,18,22],message_id:22,messageid:22,method:[1,3,6,14,18,22,23],metric:6,might:[1,18,19,23],min:23,min_supported_temperatur:[13,23],mind:19,minimum:13,mixin:[5,6,7,8,9,10,11,12,23],mode:[9,22,23],model:[1,3,6,23],modul:19,moment:18,monitor:23,more:[22,23],moreov:13,most:[0,1,3,19,22,23],motor:23,mount:23,mqtt:[0,1,3,18,19],mqtt_host:22,mqtt_port:22,ms100:[13,23],ms100sensor:[16,19,23],msl120:[9,23],msl120b:23,mss210:22,mss310:23,mts100v3:23,mts100v3valv:[16,19,23],multi:1,must:[1,9,18,22,23],name:[0,1,2,22,23],namespac:[1,22],need:[1,3,7,18,23],neighborhood:22,network:[0,1,3,19,22],new_temp:23,none:[1,2,3,6,7,9,12,14],note:[6,9,19,23],notic:18,notif:[1,3,18,19],now:[19,22],number:[0,14,18,23],numer:22,object:[0,1,6,18],obtain:22,occur:18,off:[9,12,23],offer:[6,13,23],offici:19,often:6,ofter:14,on_off:23,onc:[0,22,23],one:[0,9,22,23],ones:18,onli:[1,3,9,20,22,23],onlin:[0,1,3,23],online_statu:[1,3,23],onlinestatu:23,onoff:9,open:[7,19,22],open_statu:23,oper:[1,7,9,12,23],operations__:9,option:[2,6,7,9,12,14,23],order:[0,14,18,22,23],origin:0,other:[1,18,22,23],otherwis:[7,9],outcom:22,over:0,over_limit_delay_second:0,over_limit_threshold_percentag:0,own:23,page:19,pair:19,panoram:23,param:1,paramet:[0,1,3,5,6,7,9,12,14,22],parti:19,pass:[0,23],password:[0,22,23],path:22,pattern:[18,19],payload:22,per:0,percentag:0,perform:[0,18,19,22],phase:22,physic:22,piec:19,pip:20,pipi:20,place:19,plai:[0,23],plan:19,pleas:[6,9,19],plu:[1,3],plug:[22,23],plug_ip_address:22,plugin:[3,6,19],point:[22,23],polici:0,poll:[3,6,14],port:22,portion:22,possibl:22,post:22,power:[5,6,23],powerinfo:6,preced:18,prefix:[1,3,22],preset:14,press:[0,22,23],pretti:0,prevent:[0,18],previous:[1,6,18],print:23,proactoreventloop:18,probabl:19,proce:0,product:19,program:[0,1,3,19],proper:23,properli:18,properti:[1,3,13,14,23],protocol:19,provid:[19,22],proxim:23,publish:22,pull:22,push:[1,3,18,19],put:22,python:[18,19,20,23],quick:19,quickli:23,quit:23,rais:0,randint:23,random:23,randomli:23,rate:[18,19],ratelimitexceed:0,rather:[0,6,23],reach:[0,18],react:1,read:[5,6,19],readabl:23,realli:23,reason:[0,18,19,23],reboot:22,receiv:[1,3,18,22],recent:[6,23],recipi:23,recogn:22,red:9,refer:[6,19,23],refresh:[6,13],regist:[0,1,5,23],register_push_notification_handler_coroutin:1,relat:18,releas:[0,18],reli:[6,14,19,23],remot:0,remov:[0,18],report:[0,13,14,22,23],repres:22,represent:1,republish:22,request:[0,18,22],requests_per_second_limit:0,requir:20,respons:[0,22,23],restor:18,result:18,resum:22,retriev:[14,22,23],revers:22,revis:1,rgb:[9,23],right:19,risk:23,room:14,rout:22,run:[0,1,3,18],run_until_complet:23,runtimeerror:18,safe:23,sampl:[13,14,23],sample_timestamp:6,scan:22,script:[18,23],search:[19,23],second:[0,22],secret:22,section:[18,22,23],secur:[0,18,22],seem:[19,22],select:0,send:[0,7,18,22,23],sens:[6,13,23],sensit:0,sensor:[13,14,19],sent:[0,22],separ:22,sequenc:22,seriou:22,serv:[0,22],server:22,set:[0,14,22,23],set_event_loop_polici:[18,23],settabl:13,setup:[18,23],should:[0,1,6,14,18,19,22,23],show:23,sign:22,signal:23,signatur:[1,22,23],simpl:22,simpli:[0,22],simul:23,sinc:22,situat:18,sleep:23,smart:[0,12,23],snif:[0,22],sniff:19,sniffer:0,snippet:23,solv:18,some:[1,3,18,19,23],somehow:23,someon:[18,23],soon:23,sourc:20,specif:[0,1,22,23],specifi:[9,12],spoof:22,sprai:10,spraymixin:[16,19],ssid:22,ssl:22,start:[0,18,19,22],stat:12,state:[1,9,12,18,22,23],statu:[0,1,3,7,12,18,23],step:22,still:22,stop:0,str1:22,str2:22,str:[1,2,3,4,5,6,7,8,9,10,11,12,13,14],straight:23,strictli:[1,3],string:[14,22],strongli:0,stuff:19,subdevic:[13,14,23],subdevice_id:[3,13,14],subscrib:22,success:22,suffix:[1,3],support:[0,9,12,13,14,23],sure:[0,18,20],suspend:18,suspens:18,system:11,systemallmixin:[16,19],systemonlinemixin:[16,19],take:19,taken:23,target:23,target_temperatur:23,task:19,tbd:21,team:[0,18],tell:[9,22],temp:23,temperatur:[9,13,14,23],test:0,than:[0,6,23],thei:23,them:[0,23],themselv:23,thermostat:19,thi:[0,1,3,5,6,9,12,13,14,18,20,22,23],thing:[19,23],though:0,three:9,threshold:0,time:[13,14,18,19,22,23],timestamp:22,toggl:[9,12,23],togglemixin:[16,19,23],togglex:[9,12],togglexmixin:[16,19,23],togglexmixn:23,token:[0,18],too:[18,19],tool:0,top:18,topic:[19,22],traffic:[19,22],treat:22,tri:22,trigger:13,tropic:22,tupl:9,ture:23,turn:[9,12,23],two:[0,22],txt:20,type:[1,22,23],unavail:1,uncom:23,underscor:22,understand:19,unfortun:23,union:1,uniqu:22,unknown:1,unoffici:19,unregist:1,unregister_push_notification_handler_coroutin:1,unsupport:19,untrust:22,unzip:20,updat:[1,3,13,14,18,22,23],upgrad:20,upload:0,upon:[1,3],use:[0,14,18,19,22,23],used:[1,3,9,18,19,22,23],user:[0,1,18,22,23],user_id:22,userid:22,usernam:22,uses:22,using:[0,18,22],usual:[9,18],utc:[13,14],util:0,uuid:1,valid:22,valu:[0,6,9,13,14,23],valv:23,vari:9,veri:23,version:[0,1,18],via:[9,22,23],voltag:[6,23],wai:[0,18,19],wait:[0,23],want:[0,13,19,20,23],warn:18,warranti:19,well:[19,23],when:[0,1,3,9,12,13,14,18,23],whenev:1,where:[0,6,9,22],which:[0,7,18,22,23],why:23,wifi:22,window:[18,23],windowsselectoreventlooppolici:[18,23],within:23,without:[18,22],won:22,word:22,work:[18,19,20,23],would:23,write:[18,22,23],wrong:18,yet:0,you:[0,1,3,6,13,14,18,19,20,23],your:[0,1,3,18,23],your_meross_cloud_email:23,your_meross_cloud_password:23,zip:0},titles:["Advanced topics","BaseDevice","ChannelInfo","GenericSubDevice","HubDevice","ConsumptionXMixin","ElectricityMixin","GarageOpenerMixin","HubMixn","LightMixin","SprayMixin","SystemAllMixin","ToggleXMixin","Ms100Sensor","Mts100v3Valve","HTTP Client","API Reference","MerossManager","Common gotchas","Welcome to MerossIot Library\u2019s documentation!","Installation","Meross Architecture","Meross Protocol Inspection","Quick start"],titleterms:{"switch":23,advanc:0,api:16,app:22,architectur:[21,22],basedevic:1,befor:19,bulb:23,channelinfo:2,client:[15,22],command:22,common:18,consumptionxmixin:5,content:19,control:23,data:0,devic:[0,22,23],document:19,door:23,electricitymixin:6,flow:22,garag:23,garageopenermixin:7,genericsubdevic:3,gotcha:18,http:15,hubdevic:4,hubmixn:8,hubmts100mixin:8,indic:19,inspect:22,instal:20,librari:19,lightmixin:9,limit:0,list:23,manag:0,meross:[21,22],merossiot:19,merossmanag:17,mqtt:22,ms100sensor:13,mts100v3valv:14,notif:22,open:23,pair:22,protocol:22,push:22,quick:23,rate:0,read:23,refer:16,sensor:23,sniff:0,spraymixin:10,start:23,systemallmixin:11,systemonlinemixin:11,tabl:19,thermostat:23,thi:19,togglemixin:12,togglexmixin:12,topic:0,using:19,welcom:19}})