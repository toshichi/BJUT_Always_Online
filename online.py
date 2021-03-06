# coding=utf-8
import requests
import linecache
import time
import sys
from html.parser import HTMLParser
from urllib.request import urlopen

##############################
#####       CONFIG       ##### 
##############################

# flow upper limit rate
flow_rate = 0.8

# intervals for next traffic check
lifecycle = 59

# WLAN detection
# base_url = "wlgn.bjut.edu.cn" 
# sometimes DNS goes down, we need ip address
wlan_url = "10.21.250.3"

# base_url = "lgn.bjut.edu.cn" 
# sometimes DNS goes down, we need ip address
base_url = "172.30.201.10"

# base_url6 = "lgn6.bjut.edu.cn" 
# sometimes DNS goes down, we need ip address
# use [] to include IPv6 address
base_url6 = "[2001:da8:216:30c9::2]"

# Free Plan Credit (GiB)
free_credit = 12

# Enable Export Log Function
ex_log = False
ex_logfile = "log.txt"

# Avoid SSL cert verify error for fiddler debugging
fiddler_ssl = False

# Avoid Runtime Error
avoid_error = True

##############################
#####      Variables     ##### 
##############################

retry_count = 0
wlan_status = False

def wlan_detect():
    global wlan_status
    try:
        wlan_resp = urlopen("http://" + wlan_url + "/")
        if wlan_resp.getcode() == 200:
            wlan_status = True
            print("WLAN connection detected.")
        else:
            wlan_status = False
            print("Wired connection detected.")
    except Exception as e:
        # print_log(e)
        # urlopen error means it's in wired environment
        wlan_status = False
        print("Wired connection detected.")

def heart_beat():
    try:
        headers = {
            'Connection': 'close',
        }
        r = requests.get("http://www.msftncsi.com/ncsi.txt", timeout=1, headers=headers)
        requests.adapters.DEFAULT_RETRIES = 5
        t = r.text
        print_log("Heart beat sent.")
    except:
        t = "offline"
    return t == "Microsoft NCSI"


def if_overused():
    class HtmlPar(HTMLParser):
        ct_script = 0
        flg_script = False
        used_data = ""

        def handle_starttag(self, tag, attrs):
            if len(attrs) != 0 and len(attrs[0]) != 0:
                if tag == "script" and attrs[0][1] == "JavaScript":
                    HtmlPar.ct_script = HtmlPar.ct_script + 1
                    HtmlPar.flg_script = True

        def handle_endtag(self, tag):
            if tag == "script":
                HtmlPar.flg_script = False

        def handle_data(self, data):
            if HtmlPar.flg_script and HtmlPar.ct_script == 1:
                # get used traffic
                str_idx_s = data.index("';flow='") + 8
                str_idx_e = data.index("';fsele=", str_idx_s)
                HtmlPar.used_data = data[str_idx_s:str_idx_e].rstrip()

    html_url = "http://" + base_url + "/"
    try:
        html_res = requests.get(html_url, verify=not fiddler_ssl)
        html_res.encoding = "GB2312"
    except:
        print_log("Failed to get login page.")
        if avoid_error == False:
            exit()
        else:
            return
    html_par = HtmlPar()
    # print(html_res.text)
    if not is_online(html_res):
        # not logged in
        return -1
    else:
        html_par.flg_is_online = True
        html_par.feed(html_res.text)
        try:
            print_log(str(("%.2f" % (float(html_par.used_data) / 1024))) + " MiB" '\t' + str(
                int(int(html_par.used_data) / (free_credit * 1024 * 1024) * 100)) + '%')
        except:
            return -1
        if int(html_par.used_data) / (free_credit * 1024 * 1024) < flow_rate:
            # not overused
            return 0
        else:
            # used over limit
            return 1


def get_available_account():
    f_index = open("index.txt")
    index = int(f_index.readline().strip('\n'))
    f_index.close()
    try:
        u_acc = linecache.getline("accounts.txt", index).strip('\n').split(',')
        return u_acc
    except:
        print_log("accounts used up")
        return 1


def renew_index():
    f_index = open("index.txt")
    index = int(f_index.readline().strip('\n'))
    f_index.close()
    f_index = open("index.txt", "w")
    f_index.write(str(index + 1))
    f_index.close()
    return 0


def is_online(html_res):
    class HtmlPar(HTMLParser):
        flg_title = False
        flg_success = True

        def handle_starttag(self, tag, attrs):
            if tag == 'title':
                HtmlPar.flg_title = True

        def handle_endtag(self, tag):
            if tag == 'title':
                HtmlPar.flg_title = False

        def handle_data(self, data):
            if HtmlPar.flg_title and data[0:11] == "北京工业大学上网登录窗":
                # not logged in
                HtmlPar.flg_success = False

    html_par = HtmlPar()
    html_par.feed(html_res.text)
    return html_par.flg_success


def is_success(html_res):
    class HtmlPar(HTMLParser):
        flg_title = False
        flg_success = False

        def handle_starttag(self, tag, attrs):
            if tag == 'title':
                HtmlPar.flg_title = True

        def handle_endtag(self, tag):
            if tag == 'title':
                HtmlPar.flg_title = False

        def handle_data(self, data):
            if HtmlPar.flg_title and ((data == "登录成功窗") or ("注销" in data)):
                HtmlPar.flg_success = True

    html_par = HtmlPar()
    html_par.feed(html_res.text)
    return html_par.flg_success


def logout():
    if wlan_status:
        html_url = "http://" + wlan_url + "/F.html"
    else:
        html_url = "http://" + base_url + "/F.html"
    try:
        print_log("Trying url:" + html_url)
        requests.get(html_url, verify=not fiddler_ssl)
    except:
        print_log("No need to logout or logout err.")
        return 1
    print_log("Logged out.")
    return 0


def login6():
    html_url = "http://" + base_url6 + "/"
    account = get_available_account()
    if account == 1:
        print_log("Using backup account.")
        f_bkac = open("backupac.txt")
        account = f_bkac.readline().strip('\n').split(',')
        f_bkac.close()
        back_account = True

    print_log("Logging in IPv6 " + account[0])
    html_values = {
        'DDDDD': account[0],
        'upass': account[1],
        'v46s': 2,
        'v6ip': '',
        'f4serip': '',
        '0MKKey': ''
    }
    html_res = None
    try:
        html_res = requests.post(html_url, data=html_values, verify=not fiddler_ssl)
        html_res.encoding = "GB2312"
    except:
        print_log("Could not open IPv6 login page.")
        if avoid_error == False:
            exit()
        else:
            return
    # check login result
    if is_success(html_res):
        # login successfully
        print_log("Logged in IPv6.")


def login():
    back_account = False
    while 1:
        account = get_available_account()
        if account == 1:
            print_log("Using backup account.")
            f_bkac = open("backupac.txt")
            account = f_bkac.readline().strip('\n').split(',')
            f_bkac.close()
            back_account = True

        print_log("Logging in " + account[0])
        if wlan_status:
            html_values = {
                'DDDDD': account[0],
                'upass': account[1],
                '6MKKey': '%B5%C7%C2%BC+Login'
            }
        else:
            html_values = {
                'DDDDD': account[0],
                'upass': account[1],
                'v46s': '1',
                '0MKKey': ''
            }
        if wlan_status:
            html_url = "http://" + wlan_url + "/"
        else:
            html_url = "http://" + base_url + "/"
        html_res = None
        try:
            html_res = requests.post(html_url, data=html_values, verify=not fiddler_ssl)
            html_res.encoding = "GB2312"
        except:
            print_log("Could not open login page.")
            if avoid_error == False:
                exit()
            else:
                return

        # check login result
        if is_success(html_res):
            # login successfully
            print_log("Logged in. Checking traffic.")
            traffic_status = if_overused()
            if traffic_status == 0 or back_account is True:
                # login success
                print_log("Traffic enough.")
                login6()
                return back_account
            elif traffic_status == -1:
                # not logged in
                print_log("Not logged in, try next.")
            elif traffic_status == 1:
                # overused
                print_log("Traffic used over " + (str)(flow_rate * 100) + "%, try next.")
                logout()
            renew_index()  # index the next account
        else:
            # login not success
            global retry_count
            if retry_count > 3:
                renew_index()
                retry_count = 0
                print_log("Login failure too many times, try next.")
            else:
                retry_count += 1
                print_log("Login failure, retry.")


def reset_index():
    f_index = open("index.txt", "w")
    f_index.write("1\n")
    f_index.close()


def print_log(content):
    print(time.strftime('%Y-%m-%d %H:%M:%S ', time.localtime(time.time())), end='')
    print(content)
    sys.stdout.flush()
    if ex_log:
        f_log = open(ex_logfile, "a")
        f_log.write(time.strftime('%Y-%m-%d %H:%M:%S ', time.localtime(time.time())) + str(content) + '\n')
        f_log.close()
    return


if __name__ == "__main__":
    # when accounts are used up, backup account will be put in use.
    is_back_account = False

    # loop starts
    while 1:
        wlan_detect()
        print_log("Checking traffic...")
        status = if_overused()
        if status == 0 or is_back_account is True:
            print_log("Fine")
        else:
            if status == -1:
                print_log("Offline. Log in.")
            elif status == 1:
                print_log("Traffic used over " + (str)(flow_rate * 100) + "%, changing account...")
                logout()
                renew_index()
            is_back_account = login()

        t_time = time.localtime(time.time())
        # reset log every morning
        if t_time.tm_hour == 0 and t_time.tm_min <= 5:
            # makesure not miss
            f_log = open("log.txt", "w")
            f_log.truncate()
            f_log.close()

            # reset index every month
            if t_time.tm_mday == 1:
                reset_index()
        if t_time.tm_min % 10 == 0:
            heart_beat()

        time.sleep(lifecycle)

