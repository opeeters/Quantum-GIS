# -*- coding: utf-8 -*-

"""
***************************************************************************
    Intersection.py
    ---------------------
    Date                 : August 2012
    Copyright            : (C) 2012 by Victor Olaya
    Email                : volayaf at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Victor Olaya'
__date__ = 'August 2012'
__copyright__ = '(C) 2012, Victor Olaya'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

from sextante.core.GeoAlgorithm import GeoAlgorithm
import os.path
from PyQt4 import QtGui
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
from sextante.parameters.ParameterVector import ParameterVector
from sextante.core.QGisLayers import QGisLayers
from sextante.core.GeoAlgorithmExecutionException import GeoAlgorithmExecutionException
from sextante.outputs.OutputVector import OutputVector
from sextante.algs.ftools import ftools_utils
from sextante.core.SextanteLog import SextanteLog
from sextante.parameters.ParameterBoolean import ParameterBoolean

class Intersection(GeoAlgorithm):

    INPUT = "INPUT"
    INPUT2 = "INPUT2"
    OUTPUT = "OUTPUT"
    USE_SELECTED = "USE_SELECTED"
    USE_SELECTED2 = "USE_SELECTED2"

    #===========================================================================
    # def getIcon(self):
    #    return QtGui.QIcon(os.path.dirname(__file__) + "/icons/intersect.png")
    #===========================================================================

    def processAlgorithm(self, progress):
        useSelection = self.getParameterValue(Intersection.USE_SELECTED)
        useSelection2 = self.getParameterValue(Intersection.USE_SELECTED2)
        vlayerA = QGisLayers.getObjectFromUri(self.getParameterValue(Intersection.INPUT))
        vlayerB = QGisLayers.getObjectFromUri(self.getParameterValue(Intersection.INPUT2))
        GEOS_EXCEPT = True
        FEATURE_EXCEPT = True
        vproviderA = vlayerA.dataProvider()
        allAttrsA = vproviderA.attributeIndexes()
        vproviderA.select( allAttrsA )
        vproviderB = vlayerB.dataProvider()
        allAttrsB = vproviderB.attributeIndexes()
        vproviderB.select(allAttrsB )
        # check for crs compatibility
        crsA = vproviderA.crs()
        crsB = vproviderB.crs()
        if not crsA.isValid() or not crsB.isValid():
            SextanteLog.addToLog(SextanteLog.LOG_WARNING, "Intersection. Invalid CRS. Results might be unexpected")
        else:
            if not crsA != crsB:
                SextanteLog.addToLog(SextanteLog.LOG_WARNING, "Intersection. Non-matching CRSs. Results might be unexpected")
        fields = ftools_utils.combineVectorFields(vlayerA, vlayerB)
        longNames = ftools_utils.checkFieldNameLength( fields )
        if not longNames.isEmpty():
            raise GeoAlgorithmExecutionException("Following field names are longer than 10 characters:\n" +  longNames.join('\n') )
        writer = self.getOutputFromName(Intersection.OUTPUT).getVectorWriter(fields, vproviderA.geometryType(), vproviderA.crs() )
        inFeatA = QgsFeature()
        inFeatB = QgsFeature()
        outFeat = QgsFeature()
        index = ftools_utils.createIndex( vproviderB )
        nElement = 0
        # there is selection in input layer
        if useSelection:
          nFeat = vlayerA.selectedFeatureCount()
          selectionA = vlayerA.selectedFeatures()
          # we have selection in overlay layer
          if useSelection2:
            selectionB = vlayerB.selectedFeaturesIds()
            for inFeatA in selectionA:
              nElement += 1
              progress.setPercentage(int(nElement/nFeat * 100))
              geom = QgsGeometry( inFeatA.geometry() )
              atMapA = inFeatA.attributeMap()
              intersects = index.intersects( geom.boundingBox() )
              for id in intersects:
                if id in selectionB:
                  vproviderB.featureAtId( int( id ), inFeatB , True, allAttrsB )
                  tmpGeom = QgsGeometry( inFeatB.geometry() )
                  try:
                    if geom.intersects( tmpGeom ):
                      atMapB = inFeatB.attributeMap()
                      int_geom = QgsGeometry( geom.intersection( tmpGeom ) )
                      if int_geom.wkbType() == 7:
                        int_com = geom.combine( tmpGeom )
                        int_sym = geom.symDifference( tmpGeom )
                        int_geom = QgsGeometry( int_com.difference( int_sym ) )
                      try:
                        outFeat.setGeometry( int_geom )
                        outFeat.setAttributeMap( ftools_utils.combineVectorAttributes( atMapA, atMapB ) )
                        writer.addFeature( outFeat )
                      except:
                        FEATURE_EXCEPT = False
                        continue
                  except:
                    GEOS_EXCEPT = False
                    break
          # we don't have selection in overlay layer
          else:
            for inFeatA in selectionA:
              nElement += 1
              progress.setPercentage(int(nElement/nFeat * 100))
              geom = QgsGeometry( inFeatA.geometry() )
              atMapA = inFeatA.attributeMap()
              intersects = index.intersects( geom.boundingBox() )
              for id in intersects:
                vproviderB.featureAtId( int( id ), inFeatB , True, allAttrsB )
                tmpGeom = QgsGeometry( inFeatB.geometry() )
                try:
                  if geom.intersects( tmpGeom ):
                    atMapB = inFeatB.attributeMap()
                    int_geom = QgsGeometry( geom.intersection( tmpGeom ) )
                    if int_geom.wkbType() == 7:
                      int_com = geom.combine( tmpGeom )
                      int_sym = geom.symDifference( tmpGeom )
                      int_geom = QgsGeometry( int_com.difference( int_sym ) )
                    try:
                      outFeat.setGeometry( int_geom )
                      outFeat.setAttributeMap( ftools_utils.combineVectorAttributes( atMapA, atMapB ) )
                      writer.addFeature( outFeat )
                    except:
                      FEATURE_EXCEPT = False
                      continue
                except:
                  GEOS_EXCEPT = False
                  break
        # there is no selection in input layer
        else:
          nFeat = vproviderA.featureCount()
          vproviderA.rewind()
          # we have selection in overlay layer
          if useSelection2:
            selectionB = vlayerB.selectedFeaturesIds()
            while vproviderA.nextFeature( inFeatA ):
              nElement += 1
              progress.setPercentage(int(nElement/nFeat * 100))
              geom = QgsGeometry( inFeatA.geometry() )
              atMapA = inFeatA.attributeMap()
              intersects = index.intersects( geom.boundingBox() )
              for id in intersects:
                if id in selectionB:
                  vproviderB.featureAtId( int( id ), inFeatB , True, allAttrsB )
                  tmpGeom = QgsGeometry( inFeatB.geometry() )
                  try:
                    if geom.intersects( tmpGeom ):
                      atMapB = inFeatB.attributeMap()
                      int_geom = QgsGeometry( geom.intersection( tmpGeom ) )
                      if int_geom.wkbType() == 7:
                        int_com = geom.combine( tmpGeom )
                        int_sym = geom.symDifference( tmpGeom )
                        int_geom = QgsGeometry( int_com.difference( int_sym ) )
                      try:
                        outFeat.setGeometry( int_geom )
                        outFeat.setAttributeMap( ftools_utils.combineVectorAttributes( atMapA, atMapB ) )
                        writer.addFeature( outFeat )
                      except:
                        FEATURE_EXCEPT = False
                        continue
                  except:
                    GEOS_EXCEPT = False
                    break
          # we have no selection in overlay layer
          else:
            while vproviderA.nextFeature( inFeatA ):
              nElement += 1
              progress.setPercentage(int(nElement/nFeat * 100))
              geom = QgsGeometry( inFeatA.geometry() )
              atMapA = inFeatA.attributeMap()
              intersects = index.intersects( geom.boundingBox() )
              for id in intersects:
                vproviderB.featureAtId( int( id ), inFeatB , True, allAttrsB )
                tmpGeom = QgsGeometry( inFeatB.geometry() )
                try:
                  if geom.intersects( tmpGeom ):
                    atMapB = inFeatB.attributeMap()
                    int_geom = QgsGeometry( geom.intersection( tmpGeom ) )
                    if int_geom.wkbType() == 7:
                      int_com = geom.combine( tmpGeom )
                      int_sym = geom.symDifference( tmpGeom )
                      int_geom = QgsGeometry( int_com.difference( int_sym ) )
                    try:
                      outFeat.setGeometry( int_geom )
                      outFeat.setAttributeMap( ftools_utils.combineVectorAttributes( atMapA, atMapB ) )
                      writer.addFeature( outFeat )
                    except:
                      FEATURE_EXCEPT = False
                      continue
                except:
                  GEOS_EXCEPT = False
                  break
        del writer
        if not GEOS_EXCEPT:
            SextanteLog.addToLog(SextanteLog.LOG_WARNING, "Geometry exception while computing intersection")
        if not FEATURE_EXCEPT:
            SextanteLog.addToLog(SextanteLog.LOG_WARNING, "Feature exception while computing interesection")

    def defineCharacteristics(self):
        self.name = "Intersection"
        self.group = "Vector overlay tools"
        self.addParameter(ParameterVector(Intersection.INPUT, "Input layer", ParameterVector.VECTOR_TYPE_ANY))
        self.addParameter(ParameterVector(Intersection.INPUT2, "Intersect layer", ParameterVector.VECTOR_TYPE_ANY))
        self.addParameter(ParameterBoolean(Intersection.USE_SELECTED, "Use selected features (input)", False))
        self.addParameter(ParameterBoolean(Intersection.USE_SELECTED2, "Use selected features (intersect)", False))
        self.addOutput(OutputVector(Intersection.OUTPUT, "Intersection"))
