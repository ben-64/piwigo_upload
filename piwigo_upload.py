#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Template python program

Usage
  Usage Text

Help
  Help extract

Requirements
  python-argparse
"""

import sys
import os
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import hashlib
import base64
import subprocess

class Piwigo(object):
    API={
        "pwg.getVersion":[],
        "pwg.session.login":["password","username"],
        "pwg.categories.getList":["recursive"],
        "pwg.images.exist":["md5sum_list"],
        "pwg.images.addChunk":["original_sum","position","type","data"],
    }

    def __init__(self,url,username,password):
        self.url = url
        self.username = urllib.parse.quote_plus(username)
        self.password = urllib.parse.quote_plus(password)
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor)
        self.auth()

    def do_url_request(self,uri,post):
        return self.opener.open(os.path.join(self.url,uri),data=post.encode("ascii"))

    def do_ws(self,method,**kwargs):
        param = "&".join(["method=%s" % (method,),"&".join(["%s=%s" % (k,str(v)) for k,v in kwargs.items()])])
        result = self.do_url_request("ws.php",param).read()
        try:
            xml = ET.fromstring(result)
        except:
            print(result)
        return xml

    def auth(self):
        return self.do_ws("pwg.session.login",username=self.username,password=self.password)

    def get_version(self,):
        return self.do_ws("pwg.getVersion")

    def get_list_categories(self,):
        return self.do_ws("pwg.categories.getList",recursive="true")

    def exist_picture(self,md5sum):
        return False

    def find_category_id(self,name):
        res = {}
        xml = self.get_list_categories()
        for category in xml.iter("category"):
            if category.find("name").text == name:
                return category.attrib["id"]
        raise KeyError("No category found called %s" % (name,))

    def send_with_chunks(self,img,md5,sz=500000):
        pos = 1
        for i in range(0,len(img),sz):
            data = urllib.parse.quote_plus(base64.b64encode(img[i:i+sz]).decode("ascii"))
            self.do_ws("pwg.images.addChunk",original_sum=md5,position=str(pos),type="file",data=data)
            pos += 1

    def upload(self,img,name,album_id):
        md5 = hashlib.md5(img).hexdigest()
        if self.exist_picture(md5):
            print("Picture already exists")
            return
        self.send_with_chunks(img,md5)
        try:
            self.do_ws("pwg.images.add",original_sum=md5,name=name,categories=album_id)
        except urllib.error.HTTPError as e:
            exc_info = sys.exc_info()
            if e.code == 500 and e.msg == "file already exists":
                print("%s already exists in album" % (name,))
                return 1
            else:
                raise (exc_info[0], exc_info[1], exc_info[2])
        return 0

    def upload_img(self,path,album_name):
        with open(path,"rb") as f:
            img = f.read()
        name = name=os.path.splitext(os.path.basename(path))[0]
        return self.upload(img,name,album_name)

    def upload_string_img(self,img,name,album_name):
        return self.upload(img,name,album_name)

def convert(path,percentage):
    """ Convert file and return the result """
    return subprocess.check_output(["convert","-resize","%u%%" % percentage,path,"-"])


def parse_args():
    """ Parse command line arguments """
    try:
        import argparse
    except:
        print("python-argparse is needed")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Piwigo images uploader")
    parser.add_argument("--url","-u",metavar="URL",required=True,help="URL of piwigo server")
    parser.add_argument("--login","-l",metavar="LOGIN",required=True,help="Login to use")
    parser.add_argument("--password","-p",metavar="PASSWORD",required=True,help="Password to use")
    parser.add_argument("--album","-a",metavar="ALBUM",required=True,help="Album name")
    parser.add_argument("--convert","-c",metavar="CONVERT",default=None,type=int,help="Percentage reduction")
    parser.add_argument("images",metavar="IMAGES",nargs="*",help="Images to upload")
    return parser.parse_args()

def main():
    """ Entry Point Program """
    args = parse_args()

    piwigo = Piwigo(args.url,args.login,args.password)

    try:
        album_id = piwigo.find_category_id(args.album)
    except KeyError:
        print("Unable to find %s album" % args.album)
        return 1

    for img in args.images:
        if args.convert is not None:
            data = convert(img,args.convert)
        else:
            with open(img,"rb") as f:
                data = f.read()
        if piwigo.upload_string_img(data,os.path.splitext(os.path.basename(img))[0],album_id) == 0:
            print("%s correctly uploaded" % img)

    return 0


if __name__ == "__main__":
   sys.exit(main())
