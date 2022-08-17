#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) [2021] [Joseph Zakar], [observing@gmail.com]
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
#
# Given a closed path of straight lines, this program generates a paper model of
# (1) another copy of the closed path; (2) an extrusion (or more if it exceeds the
# maximum length) represented by a strip with tabs and score lines; and (3) strips
# for covering the tabbed strips.
# 08/17/22  SMZ added code to allow for changing the solid scoreline color (dashcolor)

import inkex
import math
import copy

from inkex import PathElement, Style, TextElement
from inkex.paths import Path, Move, Line, ZoneClose
from inkex.elements._groups import Group, Layer

class pathStruct(object):
    def __init__(self):
        self.id="path0000"
        self.path=Path()
        self.enclosed=False
        self.style = None
    def __str__(self):
        return self.path
    
class pnPoint(object):
   # This class came from https://github.com/JoJocoder/PNPOLY
    def __init__(self,p):
        self.p=p
    def __str__(self):
        return self.p
    def InPolygon(self,polygon,BoundCheck=False):
        inside=False
        if BoundCheck:
            minX=polygon[0][0]
            maxX=polygon[0][0]
            minY=polygon[0][1]
            maxY=polygon[0][1]
            for p in polygon:
                minX=min(p[0],minX)
                maxX=max(p[0],maxX)
                minY=min(p[1],minY)
                maxY=max(p[1],maxY)
            if self.p[0]<minX or self.p[0]>maxX or self.p[1]<minY or self.p[1]>maxY:
                return False
        j=len(polygon)-1
        for i in range(len(polygon)):
            if ((polygon[i][1]>self.p[1])!=(polygon[j][1]>self.p[1]) and (self.p[0]<(polygon[j][0]-polygon[i][0])*(self.p[1]-polygon[i][1])/( polygon[j][1] - polygon[i][1] ) + polygon[i][0])):
                    inside =not inside
            j=i
        return inside

class Extruder(inkex.EffectExtension):
    
    def add_arguments(self, pars):
        pars.add_argument("--usermenu")
        pars.add_argument("--extrude", type=float, default=1.0,\
            help="Width of extrusion in dimensional units")
        pars.add_argument("--maxstrip", type=float, default=11.5,\
            help="Maximum length of extrusion in dimensional units")
        pars.add_argument("--tabangle", type=float, default=45.0,\
            help="Angle of tab edges in degrees")
        pars.add_argument("--tabheight", type=float, default=0.4,\
            help="Height of tab in dimensional units")
        pars.add_argument("--dashlength", type=float, default=0.1,\
            help="Length of dashline in dimensional units (zero for solid line)")
        pars.add_argument("--dashcolor", type=str, dest="dashcolor", default="#00CC00",\
            help="Color of scorelines when solid")
        pars.add_argument("--extrudeit", default="both",\
            help="What to extrude")
        pars.add_argument("--linesonwrapper", type=inkex.Boolean, dest="linesonwrapper",\
            help="Put dashlines on wrappers")
        pars.add_argument("--unit", default="in",\
            help="Dimensional units")

    #draw SVG line segment(s) between the given (raw) points
    def drawline(self, dstr, name, parent, sstr=None):
        line_style   = {'stroke':'#000000','stroke-width':'0.25','fill':'#eeeeee'}
        if sstr == None:
            stylestr = str(Style(line_style))
        else:
            stylestr = sstr
        el = parent.add(PathElement())
        el.path = dstr
        el.style = stylestr
        el.label = name

    def add_doc(self, path, apt1, apt2, offset, layer):
        stylestr = "font-size:{0};line-height:1.25;font-family:sans-serif;stroke-width:0.264583".format(offset*2)
        te = layer.add(TextElement())
        te.style = stylestr
        te.label = te.get_id()
        te.text = "1"
        te.set('x', apt1.x)
        te.set('y', apt1.y)
        te = layer.add(TextElement())
        te.style = stylestr
        te.label = te.get_id()
        te.text = "2"
        te.set('x', apt2.x)
        te.set('y', apt2.y)
        
    def pathInsidePath(self, path, testpath):
        enclosed = True
        for tp in testpath:
            # If any point in the testpath is outside the path, it's not enclosed
            if self.insidePath(path, tp) == False:
                enclosed = False
                return enclosed # True if testpath is fully enclosed in path
        return enclosed
        
    def insidePath(self, path, p):
        point = pnPoint((p.x, p.y))
        pverts = []
        for pnum in path:
            if pnum.letter == 'Z':
                pverts.append((path[0].x, path[0].y))
            else:
                pverts.append((pnum.x, pnum.y))
        isInside = point.InPolygon(pverts, True)
        return isInside # True if point p is inside path

    def makescore(self, pt1, pt2, dashlength):
        # Draws a dashed line of dashlength between two points
        # Dash = dashlength space followed by dashlength mark
        # if dashlength is zero, we want a solid line
        # Returns dashed line as a Path object
        apt1 = Line(0.0,0.0)
        apt2 = Line(0.0,0.0)
        ddash = Path()
        if math.isclose(dashlength, 0.0):
            #inkex.utils.debug("Draw solid dashline")
            ddash.append(Move(pt1.x,pt1.y))
            ddash.append(Line(pt2.x,pt2.y))
        else:
            if math.isclose(pt1.y, pt2.y):
                #inkex.utils.debug("Draw horizontal dashline")
                if pt1.x < pt2.x:
                    xcushion = pt2.x - dashlength
                    xpt = pt1.x
                    ypt = pt1.y
                else:
                    xcushion = pt1.x - dashlength
                    xpt = pt2.x
                    ypt = pt2.y
                done = False
                while not(done):
                    if (xpt + dashlength*2) <= xcushion:
                        xpt = xpt + dashlength
                        ddash.append(Move(xpt,ypt))
                        xpt = xpt + dashlength
                        ddash.append(Line(xpt,ypt))
                    else:
                        done = True
            elif math.isclose(pt1.x, pt2.x):
                #inkex.utils.debug("Draw vertical dashline")
                if pt1.y < pt2.y:
                    ycushion = pt2.y - dashlength
                    xpt = pt1.x
                    ypt = pt1.y
                else:
                    ycushion = pt1.y - dashlength
                    xpt = pt2.x
                    ypt = pt2.y
                done = False
                while not(done):
                    if(ypt + dashlength*2) <= ycushion:
                        ypt = ypt + dashlength         
                        ddash.append(Move(xpt,ypt))
                        ypt = ypt + dashlength
                        ddash.append(Line(xpt,ypt))
                    else:
                        done = True
            else:
                #inkex.utils.debug("Draw sloping dashline")
                if pt1.y > pt2.y:
                    apt1.x = pt1.x
                    apt1.y = pt1.y
                    apt2.x = pt2.x
                    apt2.y = pt2.y
                else:
                    apt1.x = pt2.x
                    apt1.y = pt2.y
                    apt2.x = pt1.x
                    apt2.y = pt1.y
                m = (apt1.y-apt2.y)/(apt1.x-apt2.x)
                theta = math.atan(m)
                msign = (m>0) - (m<0)
                ycushion = apt2.y + dashlength*math.sin(theta)
                xcushion = apt2.x + msign*dashlength*math.cos(theta)
                xpt = apt1.x
                ypt = apt1.y
                done = False
                while not(done):
                    nypt = ypt - dashlength*2*math.sin(theta)
                    nxpt = xpt - msign*dashlength*2*math.cos(theta)
                    if (nypt >= ycushion) and (((m<0) and (nxpt <= xcushion)) or ((m>0) and (nxpt >= xcushion))):
                        # move to end of space / beginning of mark
                        xpt = xpt - msign*dashlength*math.cos(theta)
                        ypt = ypt - msign*dashlength*math.sin(theta)
                        ddash.append(Move(xpt,ypt))
                        # draw the mark
                        xpt = xpt - msign*dashlength*math.cos(theta)
                        ypt = ypt - msign*dashlength*math.sin(theta)
                        ddash.append(Line(xpt,ypt))
                    else:
                        done = True
        return ddash

    def detectIntersect(self, x1, y1, x2, y2, x3, y3, x4, y4):
        td = (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4)
        if td == 0:
            # These line segments are parallel
            return False
        t = ((x1-x3)*(y3-y4)-(y1-y3)*(x3-x4))/td
        if (0.0 <= t) and (t <= 1.0):
            return True
        else:
            return False

    def orientTab(self,pt1,pt2,height,angle,theta,orient):
        tpt1 = Line(0.0,0.0)
        tpt2 = Line(0.0,0.0)
        tpt1.x = pt1.x + orient[0]*height + orient[1]*height/math.tan(math.radians(angle))
        tpt2.x = pt2.x + orient[2]*height + orient[3]*height/math.tan(math.radians(angle))
        tpt1.y = pt1.y + orient[4]*height + orient[5]*height/math.tan(math.radians(angle))
        tpt2.y = pt2.y + orient[6]*height + orient[7]*height/math.tan(math.radians(angle))
        if not math.isclose(theta, 0.0):
            t11 = Path([Move(pt1.x,pt1.y),Line(tpt1.x, tpt1.y)])
            t12 = Path([Move(pt1.x,pt1.y),Line(tpt2.x, tpt2.y)])
            thetal1 = t11.rotate(theta, [pt1.x,pt1.y])
            thetal2 = t12.rotate(theta, [pt2.x,pt2.y])
            tpt1.x = thetal1[1].x
            tpt1.y = thetal1[1].y
            tpt2.x = thetal2[1].x
            tpt2.y = thetal2[1].y
        return tpt1,tpt2

    def makeTab(self, tpath, pt1, pt2, tabht, taba):
        # tpath - the pathstructure containing pt1 and pt2
        # pt1, pt2 - the two points where the tab will be inserted
        # tabht - the height of the tab
        # taba - the angle of the tab sides
        # returns the two tab points (Line objects) in order of closest to pt1
        tpt1 = Line(0.0,0.0)
        tpt2 = Line(0.0,0.0)
        currTabHt = tabht
        currTabAngle = taba
        testAngle = 1.0
        testHt = currTabHt * 0.001
        adjustTab = 0
        tabDone = False
        while not tabDone:
            # Let's find out the orientation of the tab
            if math.isclose(pt1.x, pt2.x):
                # It's vertical. Let's try the right side
                if pt1.y < pt2.y:
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[1,0,1,0,0,1,0,-1])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[-1,0,-1,0,0,1,0,-1]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[1,0,1,0,0,1,0,-1]) # Guessed right
                else: # pt2.y < pt1.y
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[1,0,1,0,0,-1,0,1])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[-1,0,-1,0,0,-1,0,1]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[1,0,1,0,0,-1,0,1]) # Guessed right
            elif math.isclose(pt1.y, pt2.y):
                # It's horizontal. Let's try the top
                if pt1.x < pt2.x:
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[0,1,0,-1,-1,0,-1,0])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,1,0,-1,1,0,1,0]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,1,0,-1,-1,0,-1,0]) # Guessed right
                else: # pt2.x < pt1.x
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[0,-1,0,1,-1,0,-1,0])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,-1,0,1,1,0,1,0]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,-1,0,1,-1,0,-1,0]) # Guessed right

            else: # the orientation is neither horizontal nor vertical
                # Let's get the slope of the line between the points
                # Because Inkscape's origin is in the upper-left corner,
                # a positive slope (/) will yield a negative value
                slope = (pt2.y - pt1.y)/(pt2.x - pt1.x)
                # Let's get the angle to the horizontal
                theta = math.degrees(math.atan(slope))
                # Let's construct a horizontal tab
                seglength = math.sqrt((pt1.x-pt2.x)**2 +(pt1.y-pt2.y)**2)
                if slope < 0.0:
                    if pt1.x < pt2.x:
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,1,0,-1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,-1,0,-1,0]) # Guessed right
                    else: # pt1.x > pt2.x
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,-1,0,1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,-1,0,-1,0]) # Guessed right
                else: # slope > 0.0
                    if pt1.x < pt2.x:
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,1,0,-1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,-1,0,-1,0]) # Guessed right
                    else: # pt1.x > pt2.x
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,-1,0,+1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,-1,0,-1,0]) # Guessed right
            # Check to see if any tabs intersect each other
            if self.detectIntersect(pt1.x, pt1.y, tpt1.x, tpt1.y, pt2.x, pt2.y, tpt2.x, tpt2.y):
                # Found an intersection.
                if adjustTab == 0:
                    # Try increasing the tab angle in one-degree increments
                    currTabAngle = currTabAngle + 1.0
                    if currTabAngle > 88.0: # We're not increasing the tab angle above 89 degrees
                        adjustTab = 1
                        currTabAngle = taba
                if adjustTab == 1:
                    # So, try reducing the tab height in 20% increments instead
                    currTabHt = currTabHt - tabht*0.2 # Could this lead to a zero tab_height?
                    if currTabHt <= 0.0:
                        # Give up
                        currTabHt = tabht
                        adjustTab = 2
                if adjustTab == 2:
                    tabDone = True # Just show the failure
            else:
                tabDone = True
            
        return tpt1,tpt2

    def effect(self):
        layer = self.svg.get_current_layer()
        doc_layer = self.svg.add(Layer.new('Layer Doc'))
        scale = self.svg.unittouu('1'+self.options.unit)
        extrude = float(self.options.extrude) * scale
        maxstrip = float(self.options.maxstrip) * scale
        tab_angle = float(self.options.tabangle)
        tab_height = float(self.options.tabheight) * scale
        dashlength = float(self.options.dashlength) * scale
        lines_on_wrapper = self.options.linesonwrapper
        extrude_it = self.options.extrudeit
        dashcolor = self.options.dashcolor
        sstr = None
        npaths = []
        elems = []
        for selem in self.svg.selection.filter(PathElement):
            elems.append(copy.deepcopy(selem))
        if len(elems) == 0:
            raise inkex.AbortExtension("Nothing selected")
        for elem in elems:
            escale = 1.0
            backend = elem.copy() # Make a copy of it
            backend.label = elem.get_id()+'-copy'
            layer.append(backend)
            npaths.clear()
            #inkex.utils.debug(elem.attrib)
            if 'transform' in elem.attrib:
                transforms = elem.attrib['transform'].split()
                for tf in transforms:
                    if tf.startswith('scale'):
                        escale = float(tf.split('(')[1].split(')')[0])
                if 'style' in elem.attrib:
                    lsstr = elem.attrib['style'].split(';')
                    for stoken in range(len(lsstr)):
                        if lsstr[stoken].startswith('stroke-width'):
                            swt = lsstr[stoken].split(':')[1]
                            swf = str(float(swt)*escale)
                            lsstr[stoken] = lsstr[stoken].replace(swt, swf)
                        if lsstr[stoken].startswith('stroke-miterlimit'):
                            swt = lsstr[stoken].split(':')[1]
                            swf = str(float(swt)*escale)
                            lsstr[stoken] = lsstr[stoken].replace(swt, swf)
                    sstr = ";".join(lsstr)
                else:
                    sstr = None
                elem.apply_transform()
            last_letter = 'Z'
            savid = elem.get_id()
            idmod = 0
            for ptoken in elem.path.to_absolute(): # For each point in the path
                if ptoken.letter == 'M': # Starting point
                    # Hold this point in case we receive a Z
                    ptx1 = mx = ptoken.x
                    pty1 = my = ptoken.y
                    '''
                    Assign a structure to the new path. We assume that there is
                    only one path and, therefore, it isn't enclosed by a
                    sub-path. However, we'll suffix the ID, if we find a
                    sub-path.
                    '''
                    npath = pathStruct()
                    npath.enclosed = False
                    npath.id = elem.get_id()+"-"+str(idmod)
                    if sstr == None:
                        if 'style' in elem.attrib:
                            npath.style = elem.attrib['style']
                    else:
                        npath.style = sstr
                    idmod += 1
                    npath.path.append(Move(ptx1,pty1))
                else:
                    if last_letter != 'M':
                        ptx1 = ptx2
                        pty1 = pty2
                    if ptoken.letter == 'L':
                        ptx2 = ptoken.x
                        pty2 = ptoken.y
                    elif ptoken.letter == 'H':
                        ptx2 = ptoken.x
                        pty2 = pty1
                    elif ptoken.letter == 'V':
                        ptx2 = ptx1
                        pty2 = ptoken.y
                    elif ptoken.letter == 'Z':
                        ptx2 = mx
                        pty2 = my
                    else:
                        raise inkex.AbortExtension("Unrecognized path command {0}".format(ptoken.letter))
                    npath.path.append(Line(ptx2,pty2))
                    if ptoken.letter == 'Z':
                        npaths.append(npath)
                last_letter = ptoken.letter
            # check for cutouts
            if idmod > 1:
                for apath in npaths: # We test these paths to see if they are fully enclosed
                    for bpath in npaths: # by these paths
                        if self.pathInsidePath(bpath.path, apath.path):
                            apath.enclosed = True
            for opath in npaths:
                if (extrude_it == 'both') or (((extrude_it == 'cutouts') and (opath.enclosed)) or ((extrude_it == 'outline') and (not opath.enclosed))):
                    # create the extruded path
                    xpos = ypos = 0.0
                    segs = pathStruct()
                    segs.enclosed = False
                    segs.id = opath.id+"x"
                    strips = [] # Stores segs. Needed because a single strip might be larger than the paper
                    scores = [] # holds lists of individual score lines per strip
                    score = Path() # holds the combined paths individual score lines
                    sl = None
                    # create left edge of path for each segment
                    for jnode in range(0,len(opath.path)-1):
                        if jnode == 0:
                            # Let's draw the first two node numbers to show the starting point and direction
                            self.add_doc(opath.path, opath.path[jnode], opath.path[jnode+1], 0.5*tab_height, doc_layer)
                            segs.path.append(Move(xpos,ypos)) # store the first point as a Move command
                        # calculate length of segment between jnode and jnode+1
                        seglength = math.sqrt((opath.path[jnode].x - opath.path[jnode+1].x)**2 + (opath.path[jnode].y - opath.path[jnode+1].y)**2)
                        if ypos + seglength + tab_height >= maxstrip:
                            # have to cut it at last segment
                            strips.append(copy.deepcopy(segs))
                            segs = pathStruct() # start a new segment
                            segs.enclosed = False
                            segs.id = opath.id+"x"
                            ypos = 0
                            scores.append(copy.deepcopy(score))
                            score=Path()
                            segs.path.append(Move(xpos,ypos))
                        else:
                            score.append(sl) # add the horizontal scoreline for the previous point
                        ypos = ypos + seglength
                        segs.path.append(Line(xpos,ypos)) # store the rest as Line commands
                        if jnode < len(opath.path)-2:
                            # Generate score lines across extrusion (except for last one)
                            sl = self.makescore(Move(xpos,ypos), Move(extrude, ypos),dashlength)
                    strips.append(copy.deepcopy(segs))
                    scores.append(copy.deepcopy(score))
                    # create right edge of path for each segment
                    for knode in range(len(strips)):
                        rsegs = strips[knode].path.reverse().copy() # reverse path and copy it to resegs
                        for jnode in range(0,len(rsegs)):
                            if jnode == 0:
                                # Replace the Move command with a Line command
                                mx = rsegs[0].x
                                my = rsegs[0].y
                                del rsegs[0]
                                rsegs.insert(0, Line(mx,my))
                            rsegs[jnode].x = extrude # move it extrude units from the left edge
                        strips[knode].path += rsegs # combine it with left edge of segment
                        strips[knode].path.append(ZoneClose()) # and close the path
                    if opath.style != None:
                        sstr = opath.style
                    # Generate the wrappers from the extruded paths
                    for stripcnt in range(len(strips)):
                        if math.isclose(dashlength, 0.0) and (len(scores[stripcnt]) > 0):
                            if lines_on_wrapper:
                                group = Group()
                                group.label = 'g'+opath.id+'ws'+str(stripcnt)
                                self.drawline(str(strips[stripcnt].path),'wrapper'+str(stripcnt),group,sstr) # Output the model
                                linesstr = sstr #save the normal line type
                                sstr = {'stroke':dashcolor,'stroke-width':'0.25','fill':'#eeeeee'}                                
                                self.drawline(str(scores[stripcnt]),'score'+str(stripcnt)+'w',group,sstr) # Output the scorelines separately
                                sstr = linesstr
                                layer.append(group)
                            else:
                                self.drawline(str(strips[stripcnt].path),'wrapper'+str(stripcnt),layer,sstr) # Output the model
                        else:
                            if (len(scores[stripcnt]) > 0) and lines_on_wrapper:
                                self.drawline(str(strips[stripcnt].path+scores[stripcnt]),opath.id+'ws'+str(stripcnt),layer,sstr)
                            else:
                                self.drawline(str(strips[stripcnt].path),opath.id+'w'+str(stripcnt),layer,sstr)
                    # Generate the tabbed strips from the extruded paths
                    for stripcnt in range(len(strips)):
                        strip = strips[stripcnt]
                        mpath = Path()
                        score = Path()
                        for ptn in range(len(strip.path)-2):
                            if ptn == 0:
                                mpath.append(strip.path[0])
                            tabpt1, tabpt2 = self.makeTab(strip, strip.path[ptn], strip.path[ptn+1], tab_height, tab_angle)
                            mpath.append(tabpt1)
                            mpath.append(tabpt2)
                            mpath.append(strip.path[ptn+1])
                            score.append(self.makescore(strip.path[ptn], strip.path[ptn+1],dashlength))
                        scores[stripcnt].append(copy.deepcopy(score))
                        mpath.append(ZoneClose())
                        if math.isclose(dashlength, 0.0) and (len(scores[stripcnt]) > 0):
                            group = Group()
                            group.label = 'g'+opath.id+'ms'+str(stripcnt)
                            
                            self.drawline(mpath,'model'+str(stripcnt),group,sstr) # Output the model
                            linesstr = sstr #save the normal line type
                            sstr = {'stroke':dashcolor,'stroke-width':'0.25','fill':'#eeeeee'}                                
                            self.drawline(str(scores[stripcnt]),'score'+str(stripcnt)+'w',group,sstr) # Output the scorelines separately
                            sstr = linesstr
                            layer.append(group)
                        else:
                            if len(scores[stripcnt]) > 0:
                                self.drawline(str(mpath+scores[stripcnt]),opath.id+'ms'+str(stripcnt),layer,sstr)
                            else:
                                self.drawline(str(mpath),opath.id+'m'+str(stripcnt),layer,sstr)


if __name__ == '__main__':
    Extruder().run()
