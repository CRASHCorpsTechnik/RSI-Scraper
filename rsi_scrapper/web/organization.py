"""
Organization
"""
import re
import queue

from threading import Thread
from lxml import html
from lxml import etree

from .connector import Connector
from .interface import ICommand


class Organization(ICommand):
    """Organization
    """

    __url_organization = "https://robertsspaceindustries.com/orgs/{0}"
    __url_search_orgs = "https://robertsspaceindustries.com/api/orgs/getOrgs"

    def __init__(self, sid: str):
        """
        Args:
            sid (str): The Spectrum Identification (sid).
        """
        self.sid = sid

    async def execute_async(self):
        return self.execute()

    def execute(self):
        que = queue.Queue()
        threads = []

        t0 = Thread(
            target=lambda q,
            arg1: q.put(self.get_organization_info(arg1)),
            args=(que, self.sid))
        t0.start()
        threads.append(t0)

        t1 = Thread(
            target=lambda q,
            arg1: q.put(self.search_orgs(arg1)),
            args=(que, self.sid))
        t1.start()
        threads.append(t1)

        for t in threads:
            t.join()

        counter = 0
        result = {}
        while not que.empty():
            res = que.get()

            if res is None:
                return None
            elif isinstance(res, list):
                if len(res) != 0:
                    res = res[0]
                else:
                    return None

            elif isinstance(res, dict):
                if not res:
                    return None

            result.update(res)
            counter += 1

        return result

    def get_organization_info(self, sid: str):
        """Get organizaion info.

        Args:
            sid (str): The Spectrum Identification (sid).

        Returns:
            dict: Organization information.
        """
        result = {}

        url = self.__url_organization.format(sid)

        # request website
        req = Connector().request(url, method="get")

        if req is None:
            return None
        if req.status_code == 404:
            return {}
        if req.status_code != 200:
            return None

        # get html contents
        tree = html.fromstring(req.content)

        result["url"] = url
        result["sid"] = sid

        for v in tree.xpath(
            '//*[contains(@class, "logo") and contains(@class, "noshadow")]/img/@src'
        ):
            result["logo"] = Connector().url_host + v
            break

        for v in tree.xpath('//*[@id="organization"]//h1/text()'):
            result["name"] = v.strip('/ ')
            break

        result["focus"] = {}
        result["focus"]["primary"] = {}

        for v in tree.xpath('//*[contains(@class, "primary") and contains(@class, "tooltip-wrap")]/img/@src'):
            result["focus"]["primary"]["image"] = Connector().url_host + v
            break
        for v in tree.xpath('//*[contains(@class, "primary") and contains(@class, "tooltip-wrap")]/img/@alt'):
            result["focus"]["primary"]["name"] = v.strip()
            break

        result["focus"]["secondary"] = {}
        for v in tree.xpath('//*[contains(@class, "secondary") and contains(@class, "tooltip-wrap")]/img/@src'):
            result["focus"]["secondary"]["image"] = Connector().url_host + v
            break
        for v in tree.xpath('//*[contains(@class, "secondary") and contains(@class, "tooltip-wrap")]/img/@alt'):
            result["focus"]["secondary"]["name"] = v.strip()
            break

        for v in tree.xpath('//*[contains(@class, "banner")]/img/@src'):
            result["banner"] = Connector().url_host + v
            break

        result["headline"] = {}
        for v in tree.xpath('//*[contains(@class, "body") and contains(@class, "markitup-text")]'):
            result["headline"]["html"] = etree.tostring(v, pretty_print=True).decode("utf-8")
            break

        for v in tree.xpath('//*[contains(@class, "body") and contains(@class, "markitup-text")]'):
            result["headline"]["plaintext"] = ''.join(v.itertext())
            break

        return result

    def search_orgs(self, sid: str):
        """Search organizaion by SID ()

        Args:
            sid (str): Spectrum Identification of the organization

        Returns:
            dict: Organizations found
        """

        results = []
        page = 1

        payload = {
            "activity": [],
            "commitment": [],
            "language": [],
            "model": [],
            "pagesize": 12,
            "recruiting": [],
            "roleplay": [],
            "search": sid,
            "page": page,
            "size": [],
            "sort": "name_desc"
        }

        req = Connector().request(self.__url_search_orgs, payload)

        if req is None:
            return None
        elif req.status_code == 404:
            return {}
        elif req.status_code != 200:
            return None

        # get html contents
        result = req.json()

        if result["success"] == 0:
            print(result["code"] + ": " + result["msg"])
            return None

        row_html = result["data"]["html"]
        if row_html is None or row_html.strip() == "":
            return None

        # start process html
        tree = html.fromstring(row_html)

        for i in range(1, int(tree.xpath('count(//*[contains(@class, "org-cell")])')) + 1):
            org = {}
            try:

                for v in tree.xpath('//*[contains(@class, "org-cell")][{}]/a/*[@class="left"]/*[@class="identity"]/*[@class="symbol"]/text()'.format(i)):
                    org["sid"] = v
                    break

                # ensure the right Organization is returned
                if org["sid"] != sid:
                    continue

                for v in tree.xpath('//*[contains(@class, "org-cell")][{}]/a/@href'.format(i)):
                    org["href"] = Connector().url_host + v
                    break

                for v in tree.xpath('//*[contains(@class, "org-cell")][{}]/a/*[@class="left"]/*[@class="thumb"]/img/@src'.format(i)):
                    org["logo"] = Connector().url_host + v
                    break

                for v in tree.xpath('//*[contains(@class, "org-cell")][{}]/a/*[@class="left"]/*[@class="identity"]/*[contains(@class, "name")]/text()'.format(i)):
                    org["name"] = v
                    break

                for v in tree.xpath('//*[contains(@class, "org-cell")][{}]/a/*[@class="right"]/*[@class="infocontainer"][1]/*[@class="infoitem"][1]/*[@class="value"]/text()'.format(i)):
                    org["archetype"] = v
                    break

                for v in tree.xpath('//*[contains(@class, "org-cell")][{}]/a/*[@class="right"]/*[@class="infocontainer"][1]/*[@class="infoitem"][2]/*[contains(@class, "value")]/text()'.format(i)):
                    org["lang"] = v
                    break

                for v in tree.xpath('//*[contains(@class, "org-cell")][{}]/a/*[@class="right"]/*[@class="infocontainer"][1]/*[@class="infoitem"][3]/*[contains(@class, "value")]/text()'.format(i)):
                    org["commitment"] = v
                    break

                for v in tree.xpath('//*[contains(@class, "org-cell")][{}]/a/*[@class="right"]/*[@class="infocontainer"][2]/*[@class="infoitem"][1]/*[contains(@class, "value")]/text()'.format(i)):
                    org["recruiting"] = (v == "Yes")
                    break

                for v in tree.xpath('//*[contains(@class, "org-cell")][{}]/a/*[@class="right"]/*[@class="infocontainer"][2]/*[@class="infoitem"][2]/*[contains(@class, "value")]/text()'.format(i)):
                    org["roleplay"] = (v == "Yes")
                    break

                for v in tree.xpath('//*[contains(@class, "org-cell")][{}]/a/*[@class="right"]/*[@class="infocontainer"][2]/*[@class="infoitem"][3]/*[contains(@class, "value")]/text()'.format(i)):
                    org["members"] = int(v)
                    break

                results.append(org)
            except Exception as e:
                print(e, flush=True)
                continue

        return results


class OrganizationMembers(ICommand):

    __url_organization_members = "https://robertsspaceindustries.com/api/orgs/getOrgMembers"

    def __init__(self, sid: str, **kwargs):
        self.sid = sid
        self.kwargs = kwargs

    async def execute_async(self):
        return self.execute()

    def execute(self):
        """ [public] get organization's members
            [return] assoc array with all info or None if error
            [dependency] this is a webscraping, this may not work in case of changes
        """
        result = []
        page = self.convert_val(self.kwargs.get("page"))

        json_data = {
            "symbol": self.sid,
            "search": "",
            "pagesize": 32,
            "page": page
        }

        if 'rank' in self.kwargs:
            json_data['rank'] = self.convert_val(self.kwargs.get("rank"))
        elif 'role' in self.kwargs:
            json_data['role'] = self.convert_val(self.kwargs.get("role"))
        elif 'main_org' in self.kwargs:
            json_data['main_org'] = 1 if (self.convert_val(self.kwargs.get("main_org")).lower() == 'true') else 0

        # request website
        req = Connector().request(self.__url_organization_members, json_data=json_data, method="post")

        if req is None:
            return result
        if req.status_code != 200:
            return result
        res = req.json()

        if res['success'] == 0:
            if res['code'] == 'ErrApiThrottled':
                print("Failed, retrying", flush=True)
            else:
                print(f"Failed ({res['msg']})", flush=True)
            return result

        if res['data']['html'] == '':
            return result

        # get html contents
        tree = html.fromstring(res["data"]["html"])
        index = 1
        for _ in tree.xpath("//*[contains(@class, 'member-item')]"):
            user = {}

            for v in tree.xpath(f"//*[contains(@class, 'member-item')][{index}]//*[contains(@class, 'nick')]/text()"):
                user["handle"] = v.strip()
                break

            # check if the handle is already in result
            if user["handle"] in result:
                continue

            for v in tree.xpath(f"//*[contains(@class, 'member-item')][{index}]//*[contains(@class, ' name')]/text()"):
                user["display"] = v.strip()
                break

            for v in tree.xpath(f"//*[contains(@class, 'member-item')][{index}]//*[contains(@class, 'stars') and contains(@style, .)]"):
                style = v.attrib["style"]
                match = re.search(":\\s*([0-9]*)\\%", style, re.IGNORECASE)
                if match:
                    user["stars"] = int(int(match.group(1)) / 20)
                break

            for v in tree.xpath(f"//*[contains(@class, 'member-item')][{index}]//*[contains(@class, 'rank')]"):
                if v.attrib['class'] == 'rank':
                    user["rank"] = v.text.strip()
                    break

            user["roles"] = []
            for v in tree.xpath(f"//*[contains(@class, 'member-item')][{index}]//*[contains(@class, 'rolelist')]/li/text()"):
                user["roles"].append(v)

            for v in tree.xpath(f"//*[contains(@class, 'member-item')][{index}]//img/@src"):
                user["image"] = Connector().url_host + v.strip()
                break

            # some fields are filled of "&nbsp", so skip them
            if user != {} and user["handle"] != "":
                result.append(user)
            index += 1

        return result
