#!/usr/bin/python3

# Import libraries
import time
import datetime
import requests
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.firefox.options import Options

from dateutil.relativedelta import relativedelta
import pytz
from pytz import timezone
import simplejson as json
import urllib.request
import urllib.error
import urllib.parse

import PyPDF2
import io
import urllib.request

firefoxOptions = None
firefoxDriver = None


def loginToAlpaEss():
    global exchangeRowsAirbank
    global firefoxDriver
    global firefoxOptions

    try:
        print("Start Firefox")
        firefoxOptions = Options()
        firefoxOptions.add_argument('-headless')
        firefoxDriver = webdriver.Firefox(options=firefoxOptions, executable_path=r'/home/pi/scripts/python/home_logic/bin/geckodriver', service_log_path='/home/pi/log/alpha-ess-t10_mqtt.log')
        print("Get login elements")
        firefoxDriver.get("https://www.alphaess.com/login?redirect=%2Fdashboard#")
        time.sleep(1)
        # username = firefoxDriver.find_element_by_css_selector("input[type='text']")
        username = firefoxDriver.find_element_by_xpath("//input[@placeholder='Username']")
        # password = firefoxDriver.find_element_by_css_selector("input[type='password']")
        password = firefoxDriver.find_element_by_xpath("//input[@placeholder='Password']")

        print("Send login credentials")
        username.send_keys("wooning")
        password.send_keys("6Pz#73Gvbf*W")
        # password.send_keys(Keys.ENTER)
        source1 = ""
        source1 = firefoxDriver.page_source
        print(source1)
        # print("Get Login button and send click")
        button = firefoxDriver.find_element_by_class_name("el-button--primary")
        # button.submit()
        button.click()

        time.sleep(2)
        source2 = ""
        source2 = firefoxDriver.page_source
        print("Current url:"+firefoxDriver.current_url)

        # Give the dynamic website time to build up
        time.sleep(2)
    except Exception as e:
        print("Kan alphaess.com niet inloggen, reden: %s" % str(e))
        return -1


#This function is used to get the current live exchange rate (Default)
def getDataFromAlphEss():
    try:
        pv = firefoxDriver.find_element_by_xpath('//*[@id="pane-1"]/div[2]/div[2]/div/div/ul[6]/li[1]')
        print(pv.text)
        # print("Todays generated power %1.3f" % (pv))
        return 0

    except Exception as e:
        print("getDataFromAlphEss: gaat iets fout met intrepreteren data, reden: %s" % str(e))
        return -1


loginToAlpaEss()
getDataFromAlphEss()
firefoxDriver.quit()

#pane-1 > div.el-row > div:nth-child(1) > div > div.number > p:nth-child(2)