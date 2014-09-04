#! /usr/bin/env python
# coding=utf-8
"""
    This is the "ICTS Number Distributing System"(INDS)
which is designed for distributing article/paper numbers
to teachers and students in the "Interdisciplinary Center
for Theoretical Study"(ICTS) which is a research center
for theoretical physics (String & M- theory, Cosmology,
Gravity, Particle physics, ... ). This center affiliates
to University of Science and Technology of China(USTC).

Author : Da Zhou
Email  : day.zhou.free@gmail.com

Copyright (c) 2014, Da Zhou.
License: MIT
"""

__version__ = '3.0'
__license__ = 'MIT'
#

import web
import sys, os , time
import hashlib, re
from threading import Thread

__SRC_DIR__ = os.path.dirname(__file__)

# ###################################


class INFO() :
    def __init__( self, f ) :
        names, values = [], []
        for line in f :
            if line.startswith( '#' ) :
                name = line[1:].strip() 
                if re.match( r'[a-zA-Z_][a-zA-Z0-9_]*$', name ) :
                    names.append( name )
                else :
                    # invalid variable name
                    return
            elif line.startswith( '$' ) :
                if len( names ) - len( values ) == 1 :
                    values.append( line[1:].strip() )
                else :
                    # name and value do not match
                    return
        for i, name in enumerate( names ) :
            setattr( self, name, values[i] )

# the file named "Info" should look like this
r"""
# INDS_URL
$ http://some.url
# DB_PASSWORD
$ database_password_string
# GMAIL_USERNAME
$ someone@gmail.com
# GMAIL_PASSWORD
$ gmail_password_string
"""
info = INFO( open( os.path.join( __SRC_DIR__, 'Info' ) ) )


INDS_URL = info.INDS_URL
MAIL_MSG_TAIL = u'\n\n%s\n本邮件为系统自动发送，请勿直接回复邮件到此邮箱' % ( '-' * 50 )

# Admin information
# a mail box for sending mail only
GMAIL = info.GMAIL_USERNAME
web.config.smtp_server = 'smtp.googlemail.com'
web.config.smtp_port = 587
web.config.smtp_username = GMAIL
web.config.smtp_password = info.GMAIL_PASSWORD
web.config.smtp_starttls = True
#web.config.debug = False

# Database information
DBPW = info.DB_PASSWORD

# Table names
USR = 'users'
APP = 'applicants'
PUB = 'publication'
LOG = 'errorlog'

# do not hack
DONOTHACK = 'DO NOT TRY TO HACK!'

# default maximum number shown in publication table
# about 1 years' publications
PUB_PER_PAGE = 24

# Set expiration time
web.config.session_parameters['timeout'] = 600

# URLs
urls = (
    '/(.*)/' , 'redirect' ,
    
    '/' , 'login' ,
    '/login' , 'login' ,
    '/logout' , 'logout' ,
    
    '/register' , 'register' ,
    '/forgetpassword' , 'ForgetPassword' ,
    
    '/generaluser' , 'GeneralUser' ,
    '/rootuser' , 'RootUser' ,
    '/standarduser' , 'StandardUser' ,

    '/set_censor_state' , 'SetCensorState' ,
    '/set_publication_table' , 'SetPublicationTable' ,
    '/set_users_table' , 'SetUsersTable'
)

# ###################################

def md5rand() :
    m = hashlib.md5()
    m.update( time.ctime() )
    m.update( time.ctime() )
    return m.hexdigest()[:10]

def is_number( id ) :
    try :
        int( id )
        return True
    except ValueError :
        return False

def is_valid_email( email ) :
    if len( email ) > 7 and re.match( "^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", email ) != None :
        return True

def check_password( password ) :
    if len( password ) < 6 or len( password ) > 20 :
        return False, u'密码长度应为6-20字符'
    else: 
        return True, ''

def check_pw2( password, pw2 ) :
    if pw2 != password :
        return False, u'两次输入的密码不一致'
    else :
        return True, ''

def check_email( email ) :
    if len( email ) > 50 :
        return False, u'邮箱地址应不超过50个字符'
    elif not is_valid_email( email ) :
        return False, u'无效的邮箱地址'
    elif db.select( USR , where="email='%s'" % email ) :
        return False, u'该邮箱已被使用'
    else :
        return True, ''

def write_log( arg , type ) :
    db.insert( LOG ,
        date = web.SQLLiteral( 'CURDATE()' ) ,
        time = web.SQLLiteral( 'NOW()' ) ,
        arg = arg ,
        type = type
    )

def read_log() :
    return db.select( LOG , order="id DESC" , limit=30 )

def get_admin_emails( db ) :
    emails = db.select( USR , what='email' , where="usertype='R'" )
    AdminEmails = [ em.email for em in emails ]
    if not AdminEmails :
        AdminEmails = [ GMAIL ]
    return AdminEmails


def send_email( sender=GMAIL, receiver=[GMAIL], subject='Test', content=u'For test only!' ) :
        content += MAIL_MSG_TAIL
        try :
                web.sendmail( sender , receiver , subject , content )
        except :
                pass
        #       if sending email fails,
        #       save mail infomation into databases


class class_generator :
    def __init__( self, *fields ) :
        for f in fields :
            if type( f ) != type( '' ) :
                f = str( f )
            setattr ( self , f , '' )

# ###################################    Initiate globals

db = web.database( dbn='mysql' , host='localhost' , user='inds' , db='inds' , pw=DBPW )
AdminEmails = get_admin_emails( db )
app = web.application( urls , globals() )
session = web.session.Session( app , web.session.DBStore( db , 'sessions' ) , initializer={'user':None} )
render = web.template.render( os.path.join( __SRC_DIR__ , 'templates' ) , globals={'session': session} )

# ###################################
class redirect :
    def GET( self , path ) :
        web.seeother( '/' + path )

class logout :
    def GET( self ) :
        session.kill()
        raise web.seeother( '/' )

class login :
    args = class_generator( 'username', 'password', 'fail' )
        
    def GET( self ) :
        self.args = class_generator( 'username', 'password', 'fail' )
        try :
            if session.user :    # if already logged in
                if session.user.usertype == 'R' :
                    raise web.seeother( "rootuser" )
                else :
                    raise web.seeother( "standarduser" )
            else :
                return render.index( 'FB_FORM_LOGIN', self.args )
        
        except web.SeeOther :
            return
        except Exception , e :
            write_log( e , 'LOGIN-GET' )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails, 'LOGIN-GET', e ) )

    def POST( self ) :
        try :
            f = web.input()
            user = self.check( f )
            if not user :
                self.args.username = f.username
                self.args.password = f.password
                return render.index( 'FB_FORM_LOGIN' , self.args )
            
            # if login successfully
            session.user = user
            if session.user.usertype == 'R' :
                raise web.seeother( "rootuser" )
            else :
                raise web.seeother( "standarduser" )
        
        except web.SeeOther :
            return
        except Exception , e :
            write_log( e , 'LOGIN-POST' )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails, 'LOGIN-POST', e ) )

    def check( self, f ) :
        user = self.certificate( f )
        if not user :
            self.args.fail = u'用户不存在或密码错误'
            return None
        else :
            return user
        
    def certificate( self , u ) :
        user = db.select( USR , where="username='%s' and password=PASSWORD('%s')" % ( u.username , u.password ) )
        if user :
            return user[0]
        else :
            return None

# ###################################

class register :
    def __init__( self ) :
        self.init_args()
        
    def init_args( self ) :
        self.args = class_generator(
            'username', 'info_username',
            'password', 'info_password',
            'pw2', 'info_pw2',
            'email', 'info_email',
            'realname', 'info_realname'
        )
    
    def GET( self ) :
        self.init_args()
        try :
            return render.index( 'FB_FORM_REGISTER' , self.args )
        except Exception , e :
            write_log( e , 'REGISTER-GET' )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails, 'REGISTER-GET', e ) )

    def POST( self ) :
        try :
            f = web.input()
            if not self.check( f ) :
                self.args.username = f.username
                self.args.password = f.password
                self.args.pw2 = f.pw2
                self.args.email = f.email
                self.args.realname = f.realname
                return render.index( 'FB_FORM_REGISTER', self.args )
            
            db.insert( APP ,
                username = f.username ,
                password = web.SQLLiteral( "PASSWORD('%s')" % f.password ) ,
                email = f.email ,
                realname = f.realname ,
                date=web.SQLLiteral( 'CURDATE()' )
            )
            Thread(
                target=send_email,
                kwargs={
                    'receiver': AdminEmails,
                    'subject' : u'A New Applicant for INDS',
                    'content' : u'有人提交了INDS帐号申请，请点击下面的链接处理申请：\n\n%s' % INDS_URL
                }
            ).start()
            return render.index( 'FB_MSG_REGISTER' , ( f , AdminEmails ) )
        
        except Exception , e :
            write_log( e , 'REGISTER-POST' )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails , 'REGISTER-POST', e ) )
    
    def check( self, f ) :
        flag = {}
        flag[1], self.args.info_username = self.check_username( f.username )
        flag[2], self.args.info_password = check_password( f.password )
        flag[3], self.args.info_pw2 = check_pw2( f.password, f.pw2 )
        flag[4], self.args.info_email = check_email( f.email )
        flag[5], self.args.info_realname = self.check_realname( f.realname )
        
        if flag[1] and flag[2] and flag[3] and flag[4] and flag[5] :
            return True
        else :
            return False
    
    def check_username( self, username ) :
        if not username :
            return False, u'用户名必须填写'
        elif len( username ) > 15 :
            return False, u'用户名应不超过15个字符'
        elif db.select( USR , where="username='%s'" % username ) :
            return False, u'该用户名已被使用'
        else :
            return True, ''
    
    def check_realname( self, realname ) :
        if not realname :
            return False, u'真实姓名必须填写'
        else :
            return True, ''

# ###################################

class ForgetPassword :
    args = class_generator( 'username', 'realname', 'fail' )
    
    def GET( self ) :
        self.args = class_generator( 'username', 'realname', 'fail' )
        try :
            return render.index( 'FB_FORM_FORGETPW', self.args )
        except Exception , e :
            write_log( e , 'FORGETPASSWORD-GET' )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails , 'FORGETPASSWORD-GET', e ) )
        
    def POST( self ) :
        try :
            f = web.input()
            user = self.check( f )
            if not user :
                self.args.username = f.username
                self.args.realname = f.realname
                return render.index( 'FB_FORM_FORGETPW' , self.args )
            
            useremail = user[0].email
            newpasswd = md5rand()
            db.update( USR , where="username='%s'" % f.username , password=web.SQLLiteral( "PASSWORD('%s')" % newpasswd ) )
            Thread(
                target=send_email,
                kwargs={
                    'receiver': useremail,
                    'subject' : u'Your New Password',
                    'content' : u'您在ICTS文章编号分配系统的帐户密码被重置' + \
                                u'\n\nYour New Password：%s' % newpasswd + \
                                u'\n\n请尽快使用新密码登陆并修改密码'
                }
            ).start()
            return render.index( 'FB_MSG_RESETPW_SUCCEED' , useremail )
        except Exception , e :
            write_log( e , 'FORGETPASSWORD-POST' )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails, 'FORGETPASSWORD-POST', e ) )
    
    def check( self, f ) :        
        user = db.select( USR , what='email' , where="username='%s' and realname='%s'" % ( f.username , f.realname ) )
        if not user :
            self.args.fail = u'不存在该用户或用户名和真实姓名不匹配'
            return None
        else :
            return user

# ###################################
class GeneralUser :
    def init_args( self ) :
        self.args = class_generator(
            'password', 'info_password',
            'newpassword', 'info_newpassword',
            'newpw2', 'info_newpw2',
            'newemail', 'info_newemail'
        )
    
    def __init__( self ) :
        self.init_args()
    
    def GET( self ) :
        self.init_args()
        try :
            if not session.user :
                raise web.seeother( "login" )
            
            i = web.input()
            
            if i.name == 'number' :
                return render.user( 'FB_OP_NUMBER' )
            elif i.name == 'confirm_number' :
                return self.number()
        
        except web.SeeOther :
            return
        except Exception , e :
            write_log( e , 'GENERALUSER-GET' )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails, 'GENERALUSER-GET', e ) )
    
    def number( self ) :
        year = int( time.ctime()[-4:] )
        n = db.select( PUB , what="max(number)" , where="year=%s" % year )[0]['max(number)']
        if n :
            number = int( n ) + 1
        else :
            number = 1
        
        db.insert( PUB , username=session.user.username , year=year , number=number , date=web.SQLLiteral('CURDATE()') )
        numberString = 'USTC-ICTS-%02d-%02d' % ( year-2000 , number )
        Thread(
            target=send_email,
            kwargs={
                'receiver': session.user.email,
                'subject' : 'Your requested number',
                'content' : u'您获得的ICTS文章预印本编号为：\n%s' % numberString
            }
        ).start()
        return render.user( 'FB_MSG_NUMBER' , ( numberString , ) )
    
    def POST( self ) :            # change password or email
        try :
            if not session.user :
                raise web.seeother( "login" )
            
            f = web.input()
            
            if f.has_key( 'passwd' ) :
                submit = 'passwd'
                if not self.passwd_check( f ) :
                    self.args.password = f.password
                    self.args.newpassword = f.newpassword
                    self.args.newpw2 = f.newpw2
                    return render.user( 'FB_OP_PASSWD', self.args )
            elif f.has_key( 'email' ) :
                submit = 'email'
                if not self.email_check( f ) :
                    self.args.password = f.password
                    self.args.newemail = f.newemail
                    return render.user( 'FB_OP_EMAIL', self.args )
            
            if submit == 'passwd' :
                db.update( USR , where="username='%s'" % session.user.username , password=web.SQLLiteral( "PASSWORD('%s')" % f.newpassword ) )
                Thread(
                    target=send_email,
                    kwargs={
                        'receiver': session.user.email,
                        'subject' : u'Your Password Has Changed',
                        'content' : u'您在ICTS文章编号分配系统的帐户密码已被修改' + \
                                    u'\n\nYour New Password：%s' % f.newpassword
                    }
                ).start()
                return render.user( 'FB_MSG_PWCHANGED' )
            elif submit == 'email' :
                db.update( USR , where="username='%s'" % session.user.username , email=f.newemail )
                session.user.email = f.newemail
                Thread(
                    target=send_email,
                    kwargs={
                        'receiver': f.newemail,
                        'subject' : 'Your Email Address Has Changed',
                        'content' : u'您在ICTS文章编号分配系统的帐户邮箱已被修改为当前邮箱' + \
                                    u'\n\n%s\n（如果您不知道为何收到本邮件，请忽略它）' % ( '-' * 50 )
                    }
                ).start()
                return render.user( 'FB_MSG_EMCHANGED' , ( f.newemail , ) )
        
        except web.SeeOther :
            return
        except Exception , e :
            write_log( e , 'GENERALUSER-POST' )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails, 'GENERALUSER-POST', e ) )
    
    def passwd_check( self, f ) :
        flag = {}
        flag[1], self.args.info_password = self.certificate( f.password )
        flag[2], self.args.info_newpassword = check_password( f.newpassword )
        flag[3], self.args.info_newpw2 = check_pw2( f.newpassword, f.newpw2 )
        
        if flag[1] and flag[2] and flag[3] :
            return True
        else :
            return False
    
    def email_check( self, f ) :
        flag = {}
        flag[1], self.args.info_password = self.certificate( f.password )
        flag[2], self.args.info_newemail = check_email( f.newemail )
        
        if flag[1] and flag[2] :
            return True
        else :
            return False
    
    def certificate( self , password ) :
        user = db.select( USR , where="username='%s' and password=PASSWORD('%s')" % ( session.user.username , password ) )
        if user :
            return True, ''
        else :
            return False, u'密码错误'


class RootUser( GeneralUser ) :
    def GET( self ) :
        try :
            if not session.user :
                raise web.seeother( "login" )
            
            i = web.input( name='applicants' , page=0 )
            
            if session.user.usertype == 'S' :
                return DONOTHACK
            
            if i.name == 'applicants' :
                return self.app_table()
            elif i.name == 'publication' :
                return self.pub_table( int( i.page ) )
            elif i.name == 'users' :
                return self.usr_table()
            elif i.name == 'passwd' :
                return render.user( 'FB_OP_PASSWD', self.args )
            elif i.name == 'email' :
                return render.user( 'FB_OP_EMAIL' , self.args )
            elif i.name == 'errorlog' :
                return render.user( 'FB_ERRORLOG' , ( read_log() , ) )
            elif i.name == 'help' :
                return render.user( 'FB_RT_HELP' )
        
        except web.SeeOther :
            return
        except Exception , e :
            write_log( e , 'ROOTUSER-GET-' + i.name )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails, 'ROOTUSER-GET-' + i.name, e ) )
    
    def app_table( self ) :
        app_w = db.select( APP , where="censor='W'" )
        app_p = db.select( APP , where="censor='P'" )
        app_f = db.select( APP , where="censor='F'" )
        return render.user( 'FB_SHOW_APP' , ( app_w , app_p , app_f ) )
    
    def pub_table( self , page ) :
        maxID = db.select( PUB , what="max(id)" )[0]['max(id)']
        PageLinks = []
        if not maxID :
            pub = ()
        else :
            for n in range( ( maxID - 1 ) // PUB_PER_PAGE + 1 ) :
                PageLinks.append( ( maxID - n * PUB_PER_PAGE , max( maxID - (n+1) * PUB_PER_PAGE + 1 , 1 ) ) )
            if page < 0 or page > n :
                return DONOTHACK
            pub = db.select( PUB , where="id<=%d and id>=%d" % ( PageLinks[page][0] , PageLinks[page][1] ) , order="id DESC" )
        
        return render.user( 'FB_SHOW_PUB' , ( pub , PageLinks ) )
    
    def usr_table( self ) :
        usr = db.select( USR )
        return render.user( 'FB_SHOW_USR' , ( usr , ) )


class StandardUser( GeneralUser ) :
    def GET( self ) :
        try :
            if not session.user :
                raise web.seeother( "login" )
            
            i = web.input( name='publication' , page=0 )
            
            if session.user.usertype == 'R' :
                return DONOTHACK
            
            if i.name == 'publication' :
                return self.pub_table( int ( i.page ) )
            elif i.name == 'passwd' :
                return render.user( 'FB_OP_PASSWD', self.args )
            elif i.name == 'email' :
                return render.user( 'FB_OP_EMAIL' , self.args )
            elif i.name == 'help' :
                return render.user( 'FB_STD_HELP' )
        
        except web.SeeOther :
            return
        except Exception , e :
            write_log( e , 'STANDARDUSER-GET' )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails, 'STANDARDUSER-GET', e ) )
    
    def pub_table( self , page ) :
        pub = db.select( PUB , where="username='%s'" % session.user.username , order="id DESC" )
        return render.user( 'FB_SHOW_PUB' , ( pub , [] ) )

# ###################################

class SetCensorState :
    def POST( self ) :
        try :
            if not session.user :
                raise web.seeother( 'login' )
        
            i = web.input()
            if not is_number( i.id ) :
                return render.user( 'FB_OP_CENSOR' , ( 'FB_FAIL_NEEDID' , i.id ) )
            
            app = db.select( APP , where="id=%s and censor='W'" % ( i.id ) )
            if app :
                usr = app[0]
                
                if db.select( USR , where="username='%s'" % usr.username ) :
                    db.update( APP, where="id=%s" % i.id , censor='F' )
                    return render.user( 'FB_OP_CENSOR' , ( 'FB_FAIL_USERNAME_EXIST' , usr.username ) )
                if db.select( USR , where="email='%s'" % ( usr.email ) ) :
                    db.update( APP, where="id=%s" % i.id , censor='F' )
                    return render.user( 'FB_OP_CENSOR' , ( 'FB_FAIL_EMAIL_EXIST' , usr.email ) )
                
                db.update( APP, where="id=%s" % i.id , censor=i.censor )
                if i.censor == 'P' :
                    db.insert( USR , username=usr.username , password=usr.password , email=usr.email , realname=usr.realname )
                    Thread(
                        target=send_email,
                        kwargs={
                            'receiver': usr.email,
                            'subject' : u'通过审核',
                            'content' : u'您已通过ICTS文章编号分发系统的帐号申请。\n\n' + \
                                        u'请记住您的个人信息以备将来使用。\n' + \
                                        u'用户名：%s\n密码：我不知道\n真实姓名：%s' % ( usr.username , usr.realname )
                        }
                    ).start()
                    return render.user( 'FB_OP_CENSOR' , ( 'P' , usr.username ) )
                elif i.censor == 'F' :
                    return render.user( 'FB_OP_CENSOR' , ( 'F' , usr.username ) )
            else :
                return render.user( 'FB_OP_CENSOR' , ( 'FB_FAIL_NOTEXIST' , i.id ) )
        
        except web.SeeOther :
            return
        except Exception , e :
            write_log( e , 'SET-CENSOR-POST' )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails, 'SET-CENSOR-POST', e ) )

class SetPublicationTable :
    def POST( self ) :
        try :
            if not session.user :
                raise web.seeother( 'login' )
        
            i = web.input()
        
            if i.option == 'alter' :
                return self.alter( i )
        
            elif i.option == 'delete' :
                if session.user.usertype != 'R' :
                    return DONOTHACK
                return self.delete( i.id )
        
        except web.SeeOther :
            return
        except Exception , e :
            write_log( e , 'SET-PUBLICATION-POST' )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails, 'SET-PUBLICATION-POST', e ) )
    
    def alter( self , i ) :
        if not is_number( i.id ) :
            return render.user( 'FB_OP_PUB' , ( 'FB_OP_ALTER' , 'FB_FAIL_NEEDID' , i.id ) )
        else :
            pub = db.select( PUB , what='username' , where="id='%s'" % i.id )
            if not pub :
                return render.user( 'FB_OP_PUB' , ( 'FB_OP_ALTER' , 'FB_FAIL_NOTEXIST' , i.id ) )
            elif session.user.usertype == 'S' and pub[0].username != session.user.username :
                return render.user( 'FB_OP_PUB' , ( 'FB_OP_ALTER' , 'FB_FAIL_NOTALLOWED' , i.id ) )
        
        SetValue = {}
        if i.title       : SetValue['title']       = i.title
        if i.authors     : SetValue['authors']     = i.authors
        if i.journal     : SetValue['journal']     = i.journal
        if i.arxiv_url   : SetValue['arxiv_url']   = i.arxiv_url
        if i.journal_url : SetValue['journal_url'] = i.journal_url
        
        if SetValue :
            db.update(PUB, where="id='%s'" % i.id , **SetValue )
            Thread(
                target=send_email,
                kwargs={
                    'receiver': AdminEmails,
                    'subject' : 'User changed paper infomation',
                    'content' : u'用户 <%s> <修改> 了 ID = <%s> 的记录' % ( session.user.username, i.id ) + \
                                u'\n\n点击链接查看：%s' % INDS_URL
                }
            ).start()
            return render.user( 'FB_OP_PUB' , ( 'FB_OP_ALTER' , 'FB_MSG_SUCCEED' , i.id ) )
        else :
            return render.user( 'FB_OP_PUB' , ( 'FB_OP_ALTER' , 'FB_MSG_UNCHANGED' ) )
    
    def delete( self , id ) :        
        if not is_number( id ) :
            return render.user( 'FB_OP_PUB' , ( 'FB_OP_DELETE' , 'FB_FAIL_NEEDID' , id ) )

        record = db.select( PUB , what='year,number' , where="id='%s'" % id )
        if not record :
            return render.user( 'FB_OP_PUB' , ( 'FB_OP_DELETE' , 'FB_FAIL_NOTEXIST' , id ) )
        else :
            record = record[0]
            db.delete( PUB, where="id='%s'" % id )
            Thread(
                target=send_email,
                kwargs={
                    'receiver': AdminEmails,
                    'subject' : 'User removed paper infomation',
                    'content' : u'用户 <%s> <删除> 了 ID = <%s> 的记录' % ( session.user.username, id ) + \
                                u'\n\n删除的记录原始预印本编号为：%d-%02d' % ( record['year']-2000, record['number'] ) + \
                                u'\n\n点击链接查看：%s' % INDS_URL
                }
            ).start()
            return render.user( 'FB_OP_PUB' , ( 'FB_OP_DELETE' , 'FB_MSG_SUCCEED' , id ) )

class SetUsersTable :
    def POST( self ) :
        try :
            if not session.user :
                raise web.seeother( 'login' )
            elif session.user.usertype != 'R' :
                return DONOTHACK
        
            i = web.input()
            
            if not i.username :
                return render.user( 'FB_OP_USR' , ( 'FB_FAIL_NEEDID' , ) )
            elif not db.select( USR , what='username' , where="username='%s'" % i.username ) :
                return render.user( 'FB_OP_USR' , ( 'FB_FAIL_NOTEXIST' , i.username ) )
            elif i.username == session.user.username :
                return render.user( 'FB_OP_USR' , ( 'FB_FAIL_NOTALLOWED' , ) )
        
            if i.option == 'alter' :
                db.update( USR , where="username='%s'" % i.username , usertype=i.usertype )
                return render.user( 'FB_OP_USR' , ( 'FB_MSG_ALTER_SUCCEED' , i.username ) )
            elif i.option == 'delete' :
                db.delete( USR , where="username='%s'" % i.username )
                db.update( APP , where="username='%s'" % i.username , censor='F' )
                return render.user( 'FB_OP_USR' , ( 'FB_MSG_DELETE_SUCCEED' , i.username ) )
        
        except web.SeeOther :
            return
        except Exception , e :
            write_log( e , 'SET-USERS-POST' )
            return render.index( 'FB_FAIL_UNEXPECTED' , ( AdminEmails, 'SET-USERS-POST', e ) )

# ###################################
#if __name__ == '__main__' :
application = app.wsgifunc()
#    app.run()

