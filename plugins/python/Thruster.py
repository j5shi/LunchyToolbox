# -*- coding: utf-8 -*-
"""
@author: Jia Shi
@email: j5shi@live.com
@last update: 2015-05-09 20:13:58
@version: 0.83
@license: GNU GPL v2
"""
import launchy
import subprocess
import os
import urllib
import shutil
import pprint
from PyQt4 import QtGui, QtCore


PLUGIN_NAME = "Thruster"
PLUGIN_ID = launchy.hash(PLUGIN_NAME)

LOG_LEVEL_DBG, LOG_LEVEL_INF, LOG_LEVEL_WARN, LOG_LEVEL_ERR = range(4)
LOG_LEVEL = LOG_LEVEL_INF


def logger(level, log):

    if level >= LOG_LEVEL:
        print log


class Base(object):

    def getPluginId(self):
        return PLUGIN_ID

    def getPluginName(self):
        return PLUGIN_NAME

    def getIconsPath(self, filename):
        return os.path.join(launchy.getIconsPath(), filename)

    def getCatItem(self, fullPath, shortName, pluginId, icon):
        return launchy.CatItem(fullPath, shortName, pluginId, icon)

    def getResults(self, inputDataList, resultsList):
        pass

    def getCatalog(self, resultsList):
        pass

    def getLabels(self, inputDataList):
        pass

    def launchItem(self, inputDataList, catItem):
        return False


class DspAnalyzer(Base):

    def __init__(self):

        self.id = self.getPluginId()
        self.icon = self.getIconsPath("DspAnalyzer.png")
        self.triggerTxtQueueDumpAnalyzer = "que"
        self.triggerTxts = {self.triggerTxtQueueDumpAnalyzer: "QueueDumpAnalyzer", }

    def getResults(self, inputDataList, resultsList):
        query = inputDataList[0].getText().lower()

        for triggerTxt in self.triggerTxts.keys():
            if query.startswith(triggerTxt):
                resultsList.push_front(self.getCatItem("%s: %s" % (self.getPluginName(), self.triggerTxts.get(triggerTxt)),
                                                       self.triggerTxts.get(triggerTxt),
                                                       self.id,
                                                       self.icon))

    def getQueueInfo(self, s):
        if s.strip().startswith("queueNbr"):
            return s.strip().split("=")[2]
        return None

    def getDescInfo(self, s):
        if s.strip().startswith("descPtr"):
            return s.strip().split("=")[2]
        return None

    def printToFile(self, filename, printObj):
        with open(filename, 'w') as fh:
            pprint.pprint(printObj, stream=fh)

    def QueueDumpAnalyzer(self, inputDataList, catItem):
        queueDb = {}
        queueDumpPath = inputDataList[-1].getText()

        with open(queueDumpPath) as queueDumpFh:
            queueDumps = queueDumpFh.readlines()

            for idx in range(len(queueDumps)):
                line = queueDumps[idx]
                queueInfo = self.getQueueInfo(line)

                if queueInfo:
                    queueDb.update({queueInfo: queueDb.get(queueInfo, 0)})

                    if self.getDescInfo(queueDumps[idx + 1]):
                        queueDb.update({queueInfo: queueDb.get(queueInfo) + 1})

            self.printToFile(os.path.join(os.path.dirname(queueDumpPath), "QueueDumpAnalyzer.log"), queueDb)

    def launchItem(self, inputDataList, catItem):
        if catItem.icon == self.icon:
            if inputDataList[0].getText() == self.triggerTxts.get(self.triggerTxtQueueDumpAnalyzer):
                self.QueueDumpAnalyzer(inputDataList, catItem)
            return True


class Calculator(Base):

    def __init__(self):
        self.id = self.getPluginId()
        self.icon = self.getIconsPath("Calculator.png")
        self.triggerTxt = "cal"

    def getResults(self, inputDataList, resultsList):
        query = inputDataList[0].getText().lower()

        if query.startswith(self.triggerTxt):
            if len(inputDataList) == 1:
                resultsList.push_front(self.getCatItem("%s: Calculator" % (self.getPluginName()),
                                                       "Cal",
                                                       self.id,
                                                       self.icon))

            if len(inputDataList) > 1:
                try:
                    ret = eval(inputDataList[1].getText().strip())

                    if isinstance(ret, int):
                        retInHex = "0x%x" % ret

                        retb = "{0:032b}".format(ret)
                        retInBin = ""
                        for i in range(len(retb)):
                            retInBin += retb[i] if (i % 4 or i == 0) else ("," + retb[i])
                    else:
                        retInHex = None
                        retInBin = None
                except:
                    pass
                else:
                    if ret is not None:
                        resultsList.push_front(self.getCatItem("",
                                                               "Result: %s" % (ret),
                                                               self.id,
                                                               self.icon))

                    if retInHex is not None:
                        resultsList.push_front(self.getCatItem("",
                                                               "Result: %s" % (retInHex),
                                                               self.id,
                                                               self.icon))
                    if retInBin is not None:
                        resultsList.push_front(self.getCatItem("",
                                                               "Result: %s" % (retInBin),
                                                               self.id,
                                                               self.icon))


class WebSearch(Base):

    searchEngine = {"gg": {"url": "https://www.google.com/search?q=%s", "name": "Google"},
                    "ii": {"url": "http://www.bing.com/search?q=%s", "name": "Bing"},
                    "map": {"url": "http://api.map.baidu.com/geocoder?address=%s&output=html&src=FuckYourAssBaidu", "name": "Baidu Maps"},
                    "bb": {"url": "https://www.baidu.com/s?wd=%s", "name": "Baidu"},
                    "tao": {"url": "http://s.taobao.com/search?q=%s", "name": "Taobao"},
                    "xy": {"url": "https://s.2.taobao.com/list/list.htm?q=%s&search_type=item&app=launchy", "name": "Xianyu"},
                    "jd": {"url": "http://search.jd.com/Search?keyword=%s", "name": "Jingdong"},
                    "pr": {"url": "https://pronto.inside.nsn.com/pronto/problemReportSearch.html?freeTextdropDownID=prId&searchTopText=%s", "name": "Pronto"},
                    "cpp": {"url": "http://www.cplusplus.com/search.do?q=%s", "name": "C++"},
                    "ss": {"url": "https://www.google.com/search?q=%s&sitesearch=ss64.com&gws_rd=ssl", "name": "SS64"},
                    "ieee": {"url": "http://ieeexplore.ieee.org/search/searchresult.jsp?newsearch=true&queryText=%s", "name": "IEEE"},
                    "man": {"url": "http://www.freebsd.org/cgi/man.cgi?query=%s", "name": "Linux Man Page"},
                    "cygwin": {"url": "https://cygwin.com/cgi-bin2/package-grep.cgi?grep=%s&arch=x86", "name": "cygwin package search"},
                    "all": {"url": "https://eslinw61.emea.nsn-net.net:8443/source/search?q=%s&defs=&refs=&path=&hist=&type=&project=BTS_D_CONFIG_PARAM-FZM-trunk&project=BTS_D_TRS_CI2015-trunk&project=BTS_I_COMMON_APPL-trunk&project=BTS_I_GLOBAL-trunk&project=BTS_I_ISAR_SRC-trunk&project=BTS_I_ISAR_XML-trunk&project=BTS_I_LN-trunk&project=BTS_I_PS-MAINBRANCH-trunk&project=BTS_SCM_LTE-ARCH-trunk&project=BTS_SC_BM_FZ-trunk&project=BTS_SC_BSTAT_LTE-trunk&project=BTS_SC_CCS-MAINBRANCH-trunk&project=BTS_SC_CELLP_LTE-trunk&project=BTS_SC_DSPHWAPI-MAINBRANCH-trunk&project=BTS_SC_FARECO_LTE-trunk&project=BTS_SC_L2-trunk&project=BTS_SC_LFS-trunk&project=BTS_SC_LOM-trunk&project=BTS_SC_MAC_PS_TDD-trunk&project=BTS_SC_MAC_PS_WMP-trunk&project=BTS_SC_MCUHWAPI-MAINBRANCH-trunk&project=BTS_SC_MOAM_LTE-trunk&project=BTS_SC_OAM_FZM-trunk&project=BTS_SC_PHY_TX-trunk&project=BTS_SC_PHY_TX_TDD-trunk&project=BTS_SC_SYSADAPT_LTE-trunk&project=BTS_SC_UL_PHY-fsm2-trunk&project=BTS_SC_UL_PHY-fsm3-trunk&project=BTS_SC_UL_PHY_TDD-trunk&project=BTS_T_LTETOOLS-Toolset-trunk&project=CPLANE_SC_CELLC-trunk&project=CPLANE_SC_ENBC-trunk&project=CPLANE_SC_MCEC-trunk&project=CPLANE_SC_RROM-trunk&project=CPLANE_SC_TUP-trunk&project=CPLANE_SC_UEC-trunk", "name": "OpenGrok All Projects"},
                    "dsp": {"url": "http://pscigrok-dsp.emea.nsn-net.net/source/search?q=%s&defs=&refs=&path=&hist=&type=&project=1_MAINBRANCH", "name": "OpenGrok DSPHWAPI"},
                    }

    def __init__(self):
        self.id = self.getPluginId()
        self.icon = self.getIconsPath("WebSearch.png")

    def getResults(self, inputDataList, resultsList):
        key = inputDataList[0].getText().lower()
        if key in self.searchEngine.keys():
            resultsList.push_front(self.getCatItem("%s: %s search" % (self.getPluginName(), self.searchEngine.get(key).get("name")),
                                                   "%s" % key,
                                                   self.id,
                                                   self.icon))

    def launchItem(self, inputDataList, catItem):
        if catItem.icon == self.icon:
            key = inputDataList[0].getText()
            query = urllib.quote(inputDataList[-1].getText().encode("utf8"))
            url = eval('"%s" %% "%s"' % (self.searchEngine.get(key).get('url'), query))
            subprocess.Popen('start chrome "%s"' % url, shell=True)
            return True


class RunCommands(Base):

    PROG_OS = 1        # call by OS, usually call an external program
    PROG_THRUSTER = 2  # call by Thruster, usually call a method

    CmdAlias = {"putty": {"prog": PROG_OS, "cmd": "putty.exe"},
                "sync@Company": {"prog": PROG_THRUSTER, "cmd": "self.syncCompany()"},
                "sync@Home": {"prog": PROG_THRUSTER, "cmd": "self.syncHome()"}}

    def __init__(self):
        self.id = self.getPluginId()
        self.icon = self.getIconsPath("RunCommands.png")
        self.triggerStr = "Run"

        # Get putty session from register, the session entry looks like this:
        # rsa2@22:hzling42.china.nsn-net.net    REG_SZ    0x23,0xc1ca944dc...
        proc = subprocess.Popen("reg query HKEY_CURRENT_USER\Software\SimonTatham\PuTTY\SshHostKeys /s", stdout=subprocess.PIPE)

        for line in proc.stdout.readlines():
            lineSplited = line.split()
            if len(lineSplited) >= 3:
                sessionName = lineSplited[0].split(':')[1]
                RunCommands.CmdAlias.update({sessionName: {"prog": RunCommands.PROG_OS,
                                                           "cmd": 'putty -load "%s"' % sessionName}})

    def syncFiles(self, syncTable):
        '''
        @syncTable [(local, remote), ...]: file syncing table.
        '''

        for syncEntry in syncTable:
            src, dst = syncEntry

            if (not os.path.exists(src)) and (not os.path.exists(dst)):
                logger(LOG_LEVEL_ERR, "both src and dst files not exist:\n  %s  %s." % (src, dst))
            elif os.path.exists(src) and not os.path.exists(dst):
                self.doCopy(src, dst)
            elif os.path.exists(dst) and not os.path.exists(src):
                self.doCopy(dst, src)
            elif os.path.getmtime(dst) > os.path.getmtime(src):
                self.doCopy(dst, src)
            elif os.path.getmtime(dst) < os.path.getmtime(src):
                self.doCopy(src, dst)

    def doCopy(self, src, dst):
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        elif os.path.isfile(src):
            shutil.copy2(src, dst)

    def syncCompany(self):

        syncTable = [("c:/Program Files (x86)/vim/_vimrc",
                      "d:/userdata/j5shi/BDY/Private/Vim/_vimrc"),
                     ("c:/Program Files (x86)/vim/vimfiles/bundle/snippets",
                      "d:/userdata/j5shi/BDY/Private/Vim/bundle/snippets"),
                     ("d:/userdata/j5shi/Application Data/GHISLER/wcx_ftp.ini",
                      "d:/userdata/j5shi/BDY/Private/TotalCommander/config/work/wcx_ftp.ini"),
                     ("d:/userdata/j5shi/Application Data/GHISLER/wincmd.ini",
                      "d:/userdata/j5shi/BDY/Private/TotalCommander/config/work/wincmd.ini"),
                     ("d:/userdata/j5shi/Application Data/Launchy/launchy.ini",
                      "d:/userdata/j5shi/BDY/Private/Launchy/config/company/Launchy/launchy.ini"),
                     ("d:/userdata/j5shi/My Documents/NetSarang/SECSH",
                      "d:/userdata/j5shi/BDY/Private/Tools/xshell/SECSH"),
                     ("d:/userdata/j5shi/My Documents/NetSarang/Xshell/CustomKeyMap.ckm",
                      "d:/userdata/j5shi/BDY/Private/Tools/xshell/CustomKeyMap.ckm"),
                     ("c:/apps/bin/alias.bat",
                      "d:/userdata/j5shi/BDY/Private/Apps/bin/alias.bat"), ]

        self.syncFiles(syncTable)

    def syncHome(self):

        syncTable = [("c:/Program Files (x86)/vim/_vimrc",
                      "d:/Baidu/Private/Vim/_vimrc"),
                     ("c:/Program Files (x86)/vim/vimfiles/bundle/snippets",
                      "d:/Baidu/Private/Vim/bundle/snippets"),
                     ("c:/totalcmd/wincmd.ini",
                      "d:/Baidu/Private/TotalCommander/config/home/wincmd.ini"),
                     ("c:/totalcmd/wcx_ftp.ini",
                      "d:/Baidu/Private/TotalCommander/config/home/wcx_ftp.ini"),
                     ("c:/Users/j5shi/AppData/Roaming/Launchy/launchy.ini",
                      "d:/Baidu/Private/Launchy/config/home/Launchy/launchy.ini"),
                     ("c:/Users/j5shi/Documents/NetSarang/SECSH",
                      "d:/Baidu/Private/Tools/xshell/SECSH"),
                     ("c:/Users/j5shi/Documents/NetSarang/Xshell/CustomKeyMap.ckm",
                      "d:/Baidu/Private/Tools/xshell/CustomKeyMap.ckm"),
                     ("c:/apps/bin/alias.bat",
                      "d:/Baidu/Private/apps/bin/alias.bat")]

        self.syncFiles(syncTable)

    def getResults(self, inputDataList, resultsList):
        if inputDataList[0].getText().strip().lower() == self.triggerStr.lower():
            if len(inputDataList) == 1:
                resultsList.push_front(self.getCatItem("%s: Run commands" % (self.getPluginName()),
                                                       self.triggerStr,
                                                       self.id,
                                                       self.icon))

            if len(inputDataList) > 1:
                for alias in self.CmdAlias.keys():
                    resultsList.push_front(self.getCatItem("%s: Run commands" % (self.getPluginName()),
                                                           alias,
                                                           self.id,
                                                           self.icon))

    def launchItem(self, inputDataList, catItem):
        if catItem.icon == self.icon:
            alias = self.CmdAlias.get(inputDataList[-1].getTopResult().shortName, {})

            if alias.get("prog", None) == self.PROG_OS:
                cmd = "%s" % (alias.get("cmd"))
                subprocess.Popen(cmd, shell=True)
            elif alias.get("prog", None) == self.PROG_THRUSTER:
                eval("%s" % alias.get("cmd"))
            else:
                pass

            return True


class Browser(Base):

    def __init__(self):
        self.id = self.getPluginId()
        self.icon = self.getIconsPath("Chrome.png")

    def launchItem(self, inputDataList, catItem):
        if catItem.icon == self.icon:
            subprocess.Popen('start chrome "%s"' % catItem.fullPath, shell=True)
            return True

    def getBookMarks(self, bookmarks, bookmarkBarObj):
        for obj in bookmarkBarObj:
            logger(LOG_LEVEL_DBG, "%s" % (obj.get('name')))

            if obj.get("type", '') is "folder":
                bookmarks = self.getBookMarks(bookmarks, obj.get("children", []))
            elif obj.get("type", '') is "url":
                bookmarks.update({obj.get("name", ''): obj.get("url", '')})
        return bookmarks

    def getCatalog(self, resultsList):
        """
        Callback function to asks the plugin for a static catalog to be
        added to the primary catalog. Some plugins will add permanent
        entries to Launchy primary catalog (until the catalog is rebuilt).

        It will be called when the primary catalog is rebuilt.

        @resultsList <list>: result list to append new entries (CatItem)
                             to, these will be copied over to the primary
                             catalog.
        """
        bookmarks = {}
        bookmarkFile = os.path.join(os.environ["localappdata"], "Google/Chrome/User Data/Default/Bookmarks")
        bookmarkManager = eval(open(bookmarkFile, 'r').read())
        bookmarkBar = bookmarkManager.get("roots", None).get("bookmark_bar", None).get("children", [])
        bookmarks = self.getBookMarks(bookmarks, bookmarkBar)

        for key in bookmarks.keys():
            resultsList.append(self.getCatItem(bookmarks.get(key), key, self.id, self.icon))


class Shortcuts(Base):

    def __init__(self):
        self.id = self.getPluginId()
        self.icon = self.getIconsPath("DefaultHandler.png")

    def cb_S_CR(self, inputDataList, catItem):
        subprocess.Popen('start TOTALCMD64.exe /O /A /T /R="%s"' % catItem.fullPath, shell=True)

    def cb_C_CR(self, inputDataList, catItem):
        subprocess.Popen('start TOTALCMD64.exe /O /A /T /L="%s"' % catItem.fullPath, shell=True)

    def cb_M_CR(self, inputDataList, catItem):
        subprocess.Popen('start gvim.exe --remote-tab-silent "%s"' % catItem.fullPath, shell=True)

    def cb_C_S_CR(self, inputDataList, catItem):
        subprocess.Popen('echo %s | clip' % catItem.fullPath.replace('\\', '/'), shell=True)

    def launchItem(self, inputDataList, catItem):
        if len(inputDataList) == 1:
            modifier = QtGui.QApplication.keyboardModifiers()

            if modifier == QtCore.Qt.ShiftModifier:
                self.cb_S_CR(inputDataList, catItem)
            elif modifier == QtCore.Qt.ControlModifier:
                self.cb_C_CR(inputDataList, catItem)
            elif modifier == QtCore.Qt.AltModifier:
                self.cb_M_CR(inputDataList, catItem)
            elif modifier == (QtCore.Qt.ControlModifier | QtCore.Qt.ShiftModifier):
                self.cb_C_S_CR(inputDataList, catItem)
            else:
                return False
            return True


class DefaultHandler(Base):

    def __init__(self):
        self.id = self.getPluginId()
        self.icon = self.getIconsPath("DefaultHandler.png")

    def getResults(self, inputDataList, resultsList):
        if len(inputDataList) == 1:
            resultsList.push_front(self.getCatItem("%s: default handler" % self.getPluginName(),
                                                   "",
                                                   self.id,
                                                   self.icon))

    def launchItem(self, inputDataList, catItem):

        logger(LOG_LEVEL_DBG, "Default handler query: %s" % inputDataList[0].getText().strip())

        if catItem.icon == self.icon:
            subprocess.Popen('start chrome "%s"' % inputDataList[0].getText().strip(), shell=True)
        else:
            launchy.runProgram('"%s"' % catItem.fullPath, "")
        return True


class Thruster(launchy.Plugin):

    """
    http://pylaunchy.sourceforge.net/docs/launchy.html#launchy.Plugin.launchyShow
    https://github.com/leonid-shevtsov/launchy/blob/master/plugins/verby/Verby.cpp

    This class represents a Launchy Python plugin.

    By combining a script that has a class that inherits from Plugin and
    the launchy module itself, Python scripts can be added to Launchy as
    real plugins.

    Every plugin needs to be registered using the launchy.registerPlugin() function.
    """

    def __init__(self):
        """
        Every plugin should have the following __init__ function.
        """
        launchy.Plugin.__init__(self)

        self.addons = []
        self.name = PLUGIN_NAME
        self.id = PLUGIN_ID
        self.icon = os.path.join(launchy.getIconsPath(), "%s.png" % self.name)

    def init(self):
        """
        This message informs the plugin that it is being loaded.

        This is a good time to do any initialization work.
        """
        logger(LOG_LEVEL_INF, "==============================")
        logger(LOG_LEVEL_INF, "instance created: %s" % self)
        logger(LOG_LEVEL_INF, "hash: %s" % self.getID())
        logger(LOG_LEVEL_INF, "name: %s" % self.getName())
        logger(LOG_LEVEL_INF, "icon: %s" % self.getIcon())
        logger(LOG_LEVEL_INF, "loading addons:")
        self.addons = []
        self.registerAddon(Browser)
        self.registerAddon(WebSearch)
        self.registerAddon(RunCommands)
        self.registerAddon(Calculator)
        self.registerAddon(Shortcuts)
        self.registerAddon(DspAnalyzer)
        self.registerAddon(DefaultHandler)
        logger(LOG_LEVEL_INF, "finished loading addons.")
        logger(LOG_LEVEL_INF, "==============================")

    def registerAddon(self, addon):
        a = addon()

        if type(a).__name__ != "DefaultHandler":
            self.addons.insert(0, a)
        else:
            # the DefaultHandler should always be the
            # last addon to process queries
            self.addons.append(a)

        logger(LOG_LEVEL_INF, "  - %s loaded" % type(a).__name__)

    def getID(self):
        """
        Asks the Plugin for its ID Number.

        Launchy needs an unsigned int identification value for each loaded plugin.
        You supply your own here. Typically, this is the result of hashing a string,
        as shown in the example below.

        @return <int>: plugin ID.
        """
        return self.id

    def getName(self):
        """
        Asks the plugin for its string name.

        @return <str>: plugin name.
        """
        return self.name

    def getIcon(self):
        """
        @return <str>: icon filename.
        """
        return self.icon

    def getCatalog(self, resultsList):
        """
        Callback function to asks the plugin for a static catalog to be
        added to the primary catalog. Some plugins will add permanent
        entries to Launchy primary catalog (until the catalog is rebuilt).

        It will be called when the primary catalog is rebuilt.

        @resultsList <list>: result list to append new entries (CatItem)
                             to, these will be copied over to the primary
                             catalog.
        """
        for addon in self.addons:
            addon.getCatalog(resultsList)

    def getLabels(self, inputDataList):
        """
        Asks the plugin if it would like to apply a label to the
        current search query.

        It is sometimes useful to label user queries with plugin-defined tags.

        The InputData class stores the current user query. It is in a List
        structure because each time "tab" is pressed by the user a new InputData
        is formed and appended to the list. In other words, if the user typed
        "google <tab> this is my query" then inputDataList would represent a
        list of 2 InputData classes, with the first representing "google", and
        the second, "this is my query". Each InputData can be tagged individually.

        @inputDataList <List>: list of InputData, user's search query.

        @Warning: This is called each time the user changes a character in his or
                  her query, so make sure it's fast.
        """
        for addon in self.addons:
            addon.getLabels(inputDataList)

    def getResults(self, inputDataList, resultsList):
        """
        Asks the plugin for any results to a query.

        If your plugin returns catalog results on the fly to a query (e.g. a website
        query for weby or a calculator result), then this is the place to do so. The
        existing results are stored in a ResultsList object, which is a CatItem's
        (short for Catalog Items) list. You can append your own results to it.

        @inputDataList <List>: list of InputData, user's search query.
        @resultsList <List>: ResultsList holds the catalog items that are relevent to
                             a search query. Plugins that want to add new catalog items
                             for a search query should use this class.
        """
        # handle everything by us
        inputDataList[0].setID(self.getID())

        for addon in self.addons:
            addon.getResults(inputDataList, resultsList)

    def launchItem(self, inputDataList, catItem):
        """
        Instructs the plugin that one of its own catalog items
        was selected by the user and should now be executed.

        If the plugin adds items to the catalog via getResults()
        or getCatalog() and one of those items is selected by the
        user, then it is up to the plugin to execute it when the
        user presses "enter". This is where you perform the action.

        @param inputDataList <List>: List of InputData, user's search query.
        @param catItem <CatItem>: The user selected catalog item.
        """
        for addon in self.addons:
            if addon.launchItem(inputDataList, catItem):
                logger(LOG_LEVEL_DBG, "Addon %s executed query: %s." % (type(addon).__name__, inputDataList[-1].getText()))
                break

    def hasDialog(self):
        """
        Asks the plugin if it has a dialog to display in the options menu.

        @return <bool>: true if the plugin has a dialog, or false otherwise.
        """
        pass

    def doDialog(self, parentWidget):
        """
        Tells the plugin that it's time to show its user interface.
        The function should create the widget and return it.

        - The plugin is passed a raw C++ pointer. It should be converted to QWidget
          by the user with SIP function wrapinstance.
        - SIP documentation can be found here.
        - The creation of plugin widgets should be done with PyQt4.
        - PyQt4 Documentation and Tutorial are available from PythonInfo Wiki.

        @parentWidget <void*>: The parent widget of all plugin widgets. Call wrapinstance to use it.
        @return       <void*>: The result of unwrapinstance( myPluginWidget )
        """
        pass

    def endDialog(self, accept):
        """
        Informs the plugin that it should close its dialog.

        @accept <bool>: whether the plugin should accept changes made by the
                        user while the dialog was open
        """
        pass

    def launchyShow(self):
        """
        This message informs the plugin that Launchy is now
        visible on the screen.
        """
        pass

    def launchyHide(self):
        """
        This message informs the plugin that Launchy is no
        longer visible on the screen.

        Note: this function will not be called if another
        plugin function has not returned yet (e.g. Launchy
        is hidden in the middle of launchItem()).
        """
        pass

launchy.registerPlugin(Thruster)
