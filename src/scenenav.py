import pml
from screenplay import SCENE, ACTBREAK, NOTE, ACTION, TRANSITION,\
    LB_SPACE, LB_NONE, LB_FORCED, LB_LAST
import util

import wx

# various pixel widths

# width of our navigator.
NAVIGATOR_WIDTH = 280

# Margin in the navigator.
NAVMARGIN = 3

# Mark to the left
NAV_MARK_WIDTH = 10

NAVITEM_SCENE, \
NAVITEM_NOTE, \
NAVITEM_BLURB, \
NAVITEM_TRANSITION = range(4)

# Represents an item in the scene navigator list.
class NavigatorItem():
    # one item can consist of many sublines. These are created by genLines.
    # current type of lines - scene, note, blurb, transition.
    def __init__(self, lineNo, sceneText, sceneNo = -1):
        # screenplay line attached to this item.
        self.lineNo = lineNo
        # scene number.
        self.sceneNo = sceneNo
        # number of lines in this scene
        self.sceneLen = 0

        # text that forms the item.
        self.sceneText = sceneText
        self.noteTexts = []
        self.blurbText = None
        self.tranitionText = None
        self.annotated = False

        # the lines that appear in an item, and their associated line numbers.
        self.lns = []
        self.ln_nos = []

    # does this item look the same as the another? Only compare attributes
    # that affect how the item looks.
    def hasSameText(self, another):
        if (another.sceneText != self.sceneText or\
            another.blurbText != self.blurbText or\
            another.tranitionText != self.tranitionText or\
            another.noteTexts != self.noteTexts or\
            another.lineNo != self.lineNo or\
            another.annotated != self.annotated):
            return False
        return True

    def appendNote(self, txt, line_no):
        self.noteTexts.append((txt, line_no))

    def setBlurb(self, txt):
        self.blurbText = txt

    def setTransition(self, txt):
        self.tranitionText = txt

    # Update internal sublines data
    def genLines(self):
        lns = []
        ln_nos = []

        if self.sceneNo > 0:
            lns.append((NAVITEM_SCENE, "%d. %s" %(self.sceneNo, self.sceneText)))
        else:
            lns.append((NAVITEM_SCENE, self.sceneText))
        ln_nos.append(self.lineNo)

        if self.blurbText:
            lns.append((NAVITEM_BLURB, self.blurbText))
            ln_nos.append(self.lineNo)

        for i in self.noteTexts:
            lns.append((NAVITEM_NOTE, chr(187) + " " + i[0]))
            ln_nos.append(i[1])

        if self.tranitionText:
            lns.append((NAVITEM_TRANSITION, self.tranitionText))
            ln_nos.append(self.lineNo + self.sceneLen)

        self.lns = lns
        self.ln_nos = ln_nos

    def __str__(self):
        return "\n".join(i[1] for i in self.lns) + "\n----"

# MyNavigator is our control to show a list of Scenes/Notes in a sidebar.
class MyNavigator(wx.VListBox):
    # Setup margins, data structures and fonts.
    # getCfgGui - function to get global config
    def __init__(self, parent, id, getCfgGui):
        wx.VListBox.__init__(self, parent, id, size = (NAVIGATOR_WIDTH, -1),
                style = wx.NO_BORDER)
        self.items = []
        self.currentLine = 0
        self.selectedIndex = -1
        self.subline = 0
        self.SetMargins((NAVMARGIN, NAVMARGIN))
        self.getCfgGui = getCfgGui
        self.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        self.SetItemCount(0)

        self.setFonts()
        wx.EVT_LEFT_DOWN(self, self.OnDown)
        wx.EVT_RIGHT_DOWN(self, self.OnDown)

    def setFonts(self):
        cfgGui = self.getCfgGui()
        self.scenefont = cfgGui.fonts[pml.BOLD].font

        h =  util.getFontHeight(self.scenefont)
        i = int(h*0.1)
        if i <= 1:
            smallh = h - 1
        else:
            smallh = h - i

        self.blurbfont = util.createPixelFont(
            smallh, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL)
        self.annotatedfont = util.createPixelFont(
            smallh, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.BOLD)

        self.itemheight = h + 2
        self.scenecolor = cfgGui.navSceneTextColor
        self.selscenecolor = cfgGui.navSceneSelectedMarkColor
        self.notecolor = cfgGui.navNoteTextColor
        self.blurbcolor = cfgGui.navBlurbTextColor
        self.transitioncolor = cfgGui.navTransitionTextColor
        self.bgcolor = cfgGui.navBgColor
        self.annotatedbgcolor = cfgGui.navAnnotatedBgColor
        self.separatorpen = cfgGui.tabBorderPen

    # Since VListBox provides no easy method to get the mouse position inside
    # an item when clicked, we implement our own method.
    def OnDown(self, event):
        x,y = event.GetPosition()
        count = len(self.items)
        if count == 0:
            self.selectedIndex = -1
            return
        i = self.GetFirstVisibleLine()

        height = self.OnMeasureItem(i) + (NAVMARGIN*2)
        y -= NAVMARGIN
        while y > height:
            y -= (height + NAVMARGIN)
            if i == count-1:
                break
            else:
                i += 1
            height = self.OnMeasureItem(i) + NAVMARGIN

        ln = y // self.itemheight
        if ln <0:
            ln = 0
        if ln> len(self.items[i].ln_nos)-1:
            ln = len(self.items[i].ln_nos)-1

        if i != self.selectedIndex:
            self.selectItemByIndex(i, False)
        self.subline = ln
        event.Skip()

    # called after new global settings are applied
    def fullRedraw(self):
        self.setFonts()
        self.SetItemCount(len(self.items))
        self.Refresh()

    # given a line number, return the index of element that it lies under
    def getIndexFromLineNo(self, lineno):
        if not self.items:
            return 0

        i = len(self.items) - 1
        selectedIndex = 0
        if lineno >= self.items[i].lineNo:
            return i
        else:
            while i > 0:
                if lineno < self.items[i].lineNo and \
                    lineno >= self.items[i-1].lineNo:
                    # i-1 is the index of the item to be show.
                    return i-1
                i = i-1
        # we're now at the topmost element.
        return 0

    # Select an item in the list.
    #  newIndex - index of what is to be selected.
    #  fullRefresh - if the entire list should be refreshed.
    def selectItemByIndex(self, newIndex, fullRefresh):
        if newIndex == self.selectedIndex and not fullRefresh:
            return

        oldIndex = self.selectedIndex
        self.selectedIndex = newIndex
        numItems = len(self.items)

        # The various selection hi-jinx below is to ensure the navigator
        # scroll remains constant. VListbox has a behavior, where when
        # selected, it brings the item into view. So upon new selection,
        # we save the navigator first/last values, and use these to reset
        # the scroll position.

        # The reason we select oldIndex is to make wx update that value.
        firstVisible = self.GetFirstVisibleLine()
        lastVisible = self.GetLastVisibleLine()
        if fullRefresh:
            self.SetItemCount(numItems)
        self.SetSelection(oldIndex)
        if oldIndex < firstVisible or oldIndex > lastVisible:
            if lastVisible in range(0, self.GetItemCount()):
                self.SetSelection(lastVisible)
            self.SetSelection(firstVisible)
        self.SetSelection(newIndex)
        self.SetSelection(-1)
        if fullRefresh:
            self.Refresh()

    # Check if text is different between newItems/self.Items
    def contentsChanged(self, newItems):
        if len(newItems) != len(self.items):
            return True
        i = len(newItems) - 1
        while i >= 0:
            if not newItems[i].hasSameText(self.items[i]):
                return True
            i = i-1
        return False

    # Update the navigator list
    #  items - A list containing NavigatorItem objects
    def setItems(self, sp):
        currentLine = sp.line
        items = self.getNavigatorItems(sp)
        fullRefresh = (len(items) != len(self.items)) or \
                self.contentsChanged(items)

        self.items = items
        newIndex = self.getIndexFromLineNo(currentLine)
        self.selectItemByIndex(newIndex, fullRefresh)

    # Draw separator/backgroud. We also draw the background here.
    def OnDrawSeparator(self, dc, rect, n):
        if self.items[n].sceneText:
            # if this is an annotated scene, set background
            if self.items[n].annotated:
                dc.SetPen(wx.Pen(self.annotatedbgcolor))
                dc.SetBrush(wx.Brush(self.annotatedbgcolor))
            else:
                dc.SetPen(wx.Pen(self.bgcolor))
                dc.SetBrush(wx.Brush(self.bgcolor))

            dc.DrawRectangle(rect[0], rect[1], rect[2], rect[3])

            if n == self.selectedIndex:
                dc.SetPen(wx.Pen(self.selscenecolor))
                dc.SetBrush(wx.Brush(self.selscenecolor))
                dc.DrawRectangle(rect[0], rect[1],
                    NAV_MARK_WIDTH - NAVMARGIN, rect[3])

            dc.SetPen(self.separatorpen)
            dc.DrawLine(rect[0], rect[1], rect[0]+rect[2], rect[1])

    def OnDrawBackground(self, dc, rect, n):
        #do nothing
        return

    # our custom item drawing routine.
    def OnDrawItem(self, dc, rect, index):
        item = self.items[index]
        x = rect.x + NAV_MARK_WIDTH
        i = 0
        for typ,txt in item.lns:
            y = rect.y + self.itemheight * i + 1
            if typ == NAVITEM_SCENE:
                dc.SetFont(self.scenefont)
                dc.SetTextForeground(self.scenecolor)
                util.drawText(dc, txt, x, y)
            elif typ == NAVITEM_BLURB:
                if item.annotated:
                    dc.SetFont(self.annotatedfont)
                else:
                    dc.SetFont(self.blurbfont)
                dc.SetTextForeground(self.blurbcolor)
                util.drawText(dc, txt, x , y)
            elif typ == NAVITEM_NOTE:
                dc.SetFont(self.blurbfont)
                dc.SetTextForeground(self.notecolor)
                util.drawText(dc, txt, x + 5, y)
            else:
                #NAVITEM_TRANSITION
                dc.SetFont(self.blurbfont)
                dc.SetTextForeground(self.transitioncolor)
                util.drawText(dc, txt, rect.x + rect.width - 2, y,
                                align = util.ALIGN_RIGHT)
            i += 1


    # Call when an item is clicked.
    # Returned the line number in screenplay to goto, or -1 if invalid.
    def getClickedLineNo(self):
        self.SetSelection(-1)
        if self.items:
            return self.items[self.selectedIndex].ln_nos[self.subline]
        else:
            return -1

    def OnMeasureItem(self, index):
        return self.itemheight * len(self.items[index].ln_nos)

    # Returns list of NavigatorItem objects for use in scene navigator.
    def getNavigatorItems(self, sp):
        ls = sp.lines
        navList = []
        curLine = ""
        line_no = 0

        # keep track of scene number and length
        scene_no = 1
        scene_line_nos = []
        scene_indexes = []

        #tracks the first line multiple line elements
        firstline = -1
        lineCount = len(ls)
        line_no = 0

        # start from the first scene.
        while line_no < lineCount and (ls[line_no].lt not in (SCENE, ACTBREAK)):
            line_no += 1

        while line_no < lineCount:
            line = ls[line_no]
            if not(line.lt in (NOTE, ACTION, SCENE, ACTBREAK, TRANSITION)):
                line_no += 1
                continue

            lineText = line.text
            if sp.cfg.getType(line.lt).export.isCaps:
                    lineText = util.upper(lineText)
            curLine += lineText

            lnIncremented = False

            if line.lb == LB_LAST:
                if line.lt == SCENE:
                    # Create a new item for scenes.
                    navList.append(NavigatorItem(line_no, curLine,
                                        scene_no))
                    scene_no += 1
                    scene_line_nos.append(line_no)
                    scene_indexes.append(len(navList) - 1)

                elif line.lt == ACTBREAK:
                    navList.append(NavigatorItem(line_no, curLine))
                    scene_line_nos.append(line_no)
                    scene_indexes.append(len(navList) - 1)

                elif line.lt == TRANSITION:
                    navList[-1].setTransition(curLine)

                else:
                    # NOTE or ACTION
                    # handle first line in multiline elements.
                    # if note immediately after scene, add it to that.
                    if firstline == -1:
                        ni_line = line_no
                    else:
                        ni_line = firstline

                    # Note/action after scene line.
                    if len(navList)>0 and navList[-1].lineNo == ni_line-1 and navList[-1].sceneText:
                        if line.lt == NOTE:
                            navList[-1].setBlurb(curLine)
                            navList[-1].annotated = True
                        else:
                            # ACTION
                            navList[-1].setBlurb(curLine)

                    # Note elsewhere
                    elif line.lt == NOTE:
                        navList[-1].appendNote(curLine, ni_line)

                        # Skip ahead to next line we care about
                        line_no += 1
                        while line_no < lineCount and not ls[line_no].lt in (\
                            SCENE, ACTBREAK, NOTE, TRANSITION):
                                line_no +=1
                        lnIncremented = True

                if not lnIncremented:
                    line_no += 1
                firstline = -1
                curLine = ""

            elif line.lb == LB_SPACE:
                if firstline == -1:
                    firstline = line_no
                curLine += " "
                line_no += 1

            elif line.lb == LB_FORCED:
                if firstline == -1:
                    firstline = line_no
                curLine += " "
                line_no += 1

        # update length of scenes.
        #  add final line number for last scene length.
        #  -1 so you don't count the scene line itself.
        scene_line_nos.append(line_no)

        for i  in xrange(len(scene_indexes)):
            navList[scene_indexes[i]].sceneLen = \
                scene_line_nos[i+1] - scene_line_nos[i] - 1
            # refresh internal sublines data
            navList[scene_indexes[i]].genLines()

        return navList
