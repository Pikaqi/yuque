import json
import sys
import os
import re
import requests
import psutil
import time
from datetime import datetime

if getattr(sys, 'frozen', False):
    APPLICATION_PATH = os.path.dirname(sys.executable)
else:
    APPLICATION_PATH = os.path.dirname('.')
jsonConfig = json.load(open(os.path.join(APPLICATION_PATH, "config.json"), encoding='utf-8'))


class ExportYueQueDoc:
    def __init__(self):
        try:
            if getattr(sys, 'frozen', False):
                APPLICATION_PATH = os.path.dirname(sys.executable)
            else:
                APPLICATION_PATH = os.path.dirname('.')
            self.jsonConfig = json.load(open(os.path.join(APPLICATION_PATH, "config.json"), encoding='utf-8'))
            self.base_url = self.jsonConfig['BASE_URL']
            self.token = self.jsonConfig['TOKEN']
            self.image_prefix = self.jsonConfig['IMAGE_PREFIX']
            self.image_dir = self.jsonConfig['IMAGE_DIR']
            self.headers = {
                "User-Agent": self.jsonConfig['USER_AGENT'],
                "X-Auth-Token": self.jsonConfig['TOKEN']
            }
            time = datetime.now().strftime("%Y-%m-%d")
            self.data_path = self.jsonConfig['DATA_PATH'] +"备份-"+ time
        except:
            raise ValueError("config.json 有误")

    def get_user_info(self):
        """获取用户信息"""
        res_obj = requests.get(url=self.base_url + '/user', headers=self.headers)
        if res_obj.status_code != 200:
            raise ValueError("Token 信息错误")
        user_json = res_obj.json()
        self.login_id = user_json['data']['login']
        self.uid = user_json['data']['id']
        self.username = user_json['data']['name']
        print("=========== 用户信息初始化成功 ==========")

    def get_repos_data(self):  #修改下方注释信息
        """获取知识库"""
        repos_json = requests.get(self.base_url + '/users/' + self.login_id + '/repos', headers=self.headers).json()
        #print(repos_json)
        repos_list = []
        print("=========== 获取知识库 ==========")
        for item in repos_json['data']:
            rid = item['id']  # 知识库id
            #print(rid)
            name = item['name']  # 知识库名称
            #print(name)
            if name == "资产收集":
                repos_list.append({"rid": rid, "repos_name": name})
                print(repos_list)
        #repos_list = [{'rid': 123123, 'repos_name': '库名'}] # 导出其他知识库信息知识库id：如收藏知识库
        print(repos_list)
        return repos_list
        print(repos_list)
        print("=========== 获取知识库成功 ==========")

    def get_article_data(self, repos_list):
        """获取文章数据"""
        article_list = []
        for repos in repos_list:
            article_datas = requests.get(self.base_url + '/repos/' + str(repos['rid']) + '/docs',
                                         headers=self.headers).json()
            for item in article_datas['data']:
                bid = repos['rid']
                title = item['title']  # 文章标题
                desc = item['description']
                slug = item['slug']
                article_list.append(
                    {"bid": bid, "title": title, "desc": desc, "slug": slug, "repos_name": repos["repos_name"]})

        for item in article_list:
            per_article_data = requests.get(self.base_url + '/repos/' + str(item['bid']) + '/docs/' + item['slug'],
                                            headers=self.headers).json()
            # 获取文章内容
            posts_text = re.sub(r'\\n', "\n", per_article_data['data']['body'])
            # 正则去除语雀导出的<a>标签
            result = re.sub(r'<a name="(.*)"></a>', "", posts_text)
            # 将md里的图片地址替换成本地的图片地址
            pattern = r"!\[(?P<img_name>.*?)\]" \
                      r"\((?P<img_src>https:\/\/cdn\.nlark\.com\/yuque.*\/(?P<slug>\d+)\/(?P<filename>.*?\.[a-zA-z]+)).*\)"
            repl = r"![\g<img_name>](" + self.image_prefix + "\g<filename>)"
            images = [_.groupdict() for _ in re.finditer(pattern, result)]  # 获取所有图片
            self.download_image(images, item["repos_name"])
            result = re.sub(pattern, repl, result)
            yield result, item["repos_name"], item['title']
            time.sleep(1)

    def download_image(self, images, repos_name):
        for item in images:
            # 获取网络图片资源
            # 创建文件夹
            dir_path = f"{self.data_path}/{repos_name}" + "/" + self.image_dir
            dir_ret = os.path.exists(dir_path)
            if not dir_ret:
                os.makedirs(dir_path)
            # 文件
            filepath = dir_path + f"/" + item["filename"]
            exists_ret = os.path.exists(filepath)
            if exists_ret:
                os.remove(filepath)
            # 判断响应状态
            r = requests.get(item["img_src"])
            if r.status_code == 200:
                # 创建文件保存图片
                with open(filepath, 'wb') as f:
                    # 将图片字节码写入创建的文件中
                    f.write(r.content)
            else:
                print('获取失败')

    def save_article(self, result, repos_name, title):
        """写入文章"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dir_path = f"{self.data_path}/{repos_name}"
        filepath = dir_path + f"/{title}.md"
        dir_ret = os.path.exists(dir_path)
        if not dir_ret:
            os.makedirs(dir_path)
        exists_ret = os.path.exists(filepath)
        if exists_ret:
            os.remove(filepath)
        try:
            with open(filepath, 'a', encoding="utf-8") as fp:
                fp.writelines(result)
            print(f"[{current_time}]  {title} 写入完成")
        except Exception as e:
            print(f"[{current_time}]  {title} 写入失败")

    def main(self):
        self.get_user_info()
        repos_list = self.get_repos_data()
        gen_obj = self.get_article_data(repos_list)
        for item in gen_obj:
            self.save_article(item[0], item[1], item[2])


if __name__ == "__main__":
    yq = ExportYueQueDoc()
    yq.main()

