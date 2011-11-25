#!/usr/bin/env python
"""
    Tropical Cyclone Risk Model (TCRM) - Version 1.0 (beta release)
    Copyright (C) 2011  Geoscience Australia

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.


Title: KDEOrigin.py - Define Class for KDE Origin
Author: Geoff Xu, geoff.xu@ga.gov.au
CreationDate: 2006-01-10
Description:
Python code developed from Xun Guo Lin's Matlab code on PDF &
CDF of cyclone origin using 2D KDE
Version: $Rev: 644 $

ModifiedBy: C. Arthur
ModifiedDate: 2006-10-24
Modification: Added descriptive headers and metadata

ModifiedBy: N. Habili
ModifiedDate: 2006-11-29
Modification: File names passed by dictionaries instead of individual
              file names.
Upgrade to ndarray
Conformance with style guide

ModifiedBy: N. Habili
ModifiedDate: 2006-12-14
Modification:
Results will be returned if files=0.
Removed method generateOldKde().

ModifiedBy: N. Habili
ModifiedDate: 2006-12-15
Modification:
Method name changed from generateNewKde to generateKDE

Version: 83
ModifiedBy: Craig Arthur, craig.arthur@ga.gov.au
ModifiedDate: 10/04/08 11:42:AM
Modification: Changed logging method

Version: 299
ModifiedBy: Craig Arthur, craig.arthur@ga.gov.au
ModifiedDate: 2008-07-02 2:31:PM
Modification: Write PDF & CDF to ascii grid files (these can be read
by GIS packages), eliminating the need for multiple files to be created

Version: $Rev: 644 $
ModifiedBy: Craig Arthur, craig.arthur@ga.gov.au
ModifiedDate: 2011-03-21 1:18:PM
Modification: Write 2-D grid of genesis PDF to netCDF.

Id: KDEOrigin.py 219 2009-10-02 03:20:56Z carthur $

"""

import os, sys, pdb, logging

import numpy
from scipy import array, arange
import Utilities.stats as stats
import Utilities.KPDF as KPDF
from Utilities.files import flLoadFile, flStartLog
from Utilities.config import cnfGetIniValue
from Utilities.grid import grdSave
from Utilities.nctools import ncSaveGrid, _ncSaveGrid
from Utilities.plotField import plotField


class KDEOrigin:
    """
    Parameters
    ----------
    files : dictionary
        dictionary containing input/output file names and paths.

    Members
    -------
    aus_blat : 1D array of float
        Latitidue data for Australian coast line from australia_bndy.txt
        with Tasmania removed
    aus_blon : 1D array of float
        Longitude data for Austrlian coast line from australia_bndy.txt
        with Tasmania removed
    lonLat : 1D array of float
        Longitude and latitude dataset for cyclone origins from lon_lat
        file
    kde_origin_x : string (file name including path)
        Path and name of created data for x coordinates of KDE result
    kde_origin_y : string (file name including path)
        Path and name of created data for y coordinates of KDE result
    kde_origin_z : string (file name including path)
        Path and name of created data for z coordinates of KDE result
    cdf_origin_cz : string (file name including path)
        Path and name of created data for z coordinates of CDF result

    Methods
    -------
    generateKDE(user,option,bw)
        Generate the PDF for cyclone origins using kernel density
        estimation technique then save it to a file path provided by
        user
    generateCdf()
        Generate the CDFs corresponding to PDFs of cyclone origins,
        then save it on a file path provided by user
    plotKde()
        Plot the PDF using 2D kernel density estimation technique
    plotColour()
        Wrap a colour layer on top of 3D plots, can be slow
    plotCdf()
        Plot the CDFs corresponding to pdfs of cyclone origins

    Internal Methods
    ----------------
    _generatePDF(option,grid,bw) : 1D array of float
        Sub-function that generates the PDFs of 2D kernel density
        estimation from raw dataset

    """

    def __init__(self, configFile, kdeType, gridLimit, kdeStep, lonLat=None, progressbar=None):
        """
        Initialize the required datasets
        lon & lat for cyclone origins,
        new_kde_origin coordinates for pathname to save the generated
        kde values and bw for bandwidth of kde estimates
        """
        self.logger = logging.getLogger()
        self.progressbar = progressbar
        if self.progressbar:
            KPDF.set_callback(self.updateProgressBar)
        self.logger.info("Initialising KDEOrigins")
        self.configFile = configFile
        self.x = arange(gridLimit['xMin'], gridLimit['xMax'], kdeStep)
        self.y = arange(gridLimit['yMax'], gridLimit['yMin'], -kdeStep)

        self.kdeType = kdeType
        self.kdeStep = kdeStep

        if lonLat is None:
            self.outputPath = cnfGetIniValue(self.configFile, 'Output', 'Path')
            self.processPath = os.path.join(self.outputPath, 'process')
            self.logger.debug("Loading "+os.path.join(self.processPath,
                                                  'init_lon_lat'))
            ll = flLoadFile(os.path.join(self.processPath, 'init_lon_lat'),
                            '%', ',')
            self.lonLat = ll[:,0:2]
        else:
            self.lonLat = lonLat[:,0:2]

        self.bw = KPDF.MPDFOptimumBandwidth(self.lonLat)
        self.logger.debug("Optimal bandwidth: %f"%self.bw)

    def __doc__(self):
        """
        documentation on what this class does
        """
        return "Plot tropical cyclone origins using 2D kernel density estimation technique"

    def _generatePDF(self, grid, bw):
        """
        Sub-function that generates the PDFs of 2D kernel density
        estimation from raw dataset
        """
        if bw <= 0:
            self.logger.critical("bw = %d. Bandwidth cannot be negative or zero"%bw)
            raise ValueError, 'bw = %d. Bandwidth cannot be negative or zero' %bw

        try:
            kdeMethod = getattr(KPDF, "MPDF%s" %self.kdeType)
        except AttributeError:
            self.logger.critical("Invalid input on option: KDE method 'MPDF%s' does not exist" %self.kdeType)
            raise

        return kdeMethod(self.lonLat, grid, bw)

    def generateKDE(self, bw=None, save=False):
        """
        Generate the PDF for cyclone origins using kernel density
        estimation technique then save it to a file path provided by
        user.
        """
        grid2d = KPDF.MPDF2DGrid2Array(self.x, self.y, 1)
        if bw:
            self.bw = bw
        pdf = self._generatePDF(grid2d, self.bw)
        # Normalise PDF so total probability equals one
        # Note: Need to investigate why output from KPDF is not correctly normalised
        pdf = pdf / pdf.sum()
        pdf.shape = (pdf.shape[0]/self.x.size, self.x.size)
        self.pdf = pdf.transpose()
        if save:
            outputFile = os.path.join(self.processPath, 'originPDF.nc')
            dimensions = {0:{'name':'lat','values':self.y,'dtype':'f','atts':{'long_name':'Latitude','units':'degrees_north'} },
                          1:{'name':'lon','values':self.x,'dtype':'f','atts':{'long_name':'Longitude','units':'degrees_east'} } }
            variables =  {0:{'name':'gpdf','dims':('lat','lon'),
                             'values':numpy.array(pdf),'dtype':'f',
                             'atts':{'long_name':'TC Genesis probability distribution',
                                      'units':''} } }
            _ncSaveGrid(outputFile, dimensions, variables)

            #ncSaveGrid(os.path.join(self.processPath, 'originPDF.nc'),self.x,self.y,pdf,'gpdf',"",longname='TC genesis probability')
            [gx,gy] = numpy.meshgrid(self.x,self.y)

            # Automatically determine appropriate contour levels 
            min_lvls = 6.0
            lvls_options = numpy.array([1.0, 0.5, 0.25, 0.2, 0.1])
            pdfMax = pdf.max()
            exponent = int(numpy.floor(numpy.log10(pdfMax)))
            significand = pdfMax * 10**-exponent
            lvl_step = lvls_options[numpy.where((significand/lvls_options) > min_lvls)[0][0]]
            lvls = numpy.arange(0, pdf.max(), lvl_step*(10.0**exponent))

            plotField(gx, gy, (10.0**-exponent)*pdf, res='l',levels=(10.0**-exponent)*lvls, cmap='jet', smoothing=False,
              title=None, xlab='Lonigtude', ylab='Latitude', clab=r'Genesis probability ($\times 10^{' + str(exponent) + '}$)',
              maskland=True,outputFile=os.path.join(self.outputPath, 'plots', 'stats', 'originPDF_contour.png'),
              fill=False)
            plotField(gx, gy, (10.0**-exponent)*pdf, res='l',levels=(10.0**-exponent)*lvls, cmap='jet', smoothing=False,
              title=None, xlab='Lonigtude', ylab='Latitude', clab=r'Genesis probability ($\times 10^{' + str(exponent) + '}$)',
              maskland=False,outputFile=os.path.join(self.outputPath, 'plots', 'stats', 'originPDF_fill.png'),
              fill=True)
            self.logger.debug("Saving origin PDF to file")
            #grdSave(os.path.join(self.processPath, 'originPDF.txt'),
            #        pdf, self.x, self.y, self.kdeStep)
        else:
            return self.x, self.y, self.pdf

    def generateCdf(self, save=False):
        """
        Generate the CDFs corresponding to PDFs of cyclone origins,
        then save it on a file path provided by user
        """
        self.cz = stats.cdf2d(self.x, self.y, self.pdf)
        if save:
            self.logger.debug("Saving origin CDF to file")
            grdSave(self.processPath+'originCDF.txt', self.cz, self.x,
                    self.y, self.kdeStep)
        else:
            return self.cz

    def updateProgressBar(self, n, nMax):
        """
        Callback function to update progress bar from C code
        """
        if self.progressbar:
            self.progressbar.update(n/float(nMax), 0.0, 0.7)

if __name__ == "__main__":
    try:
        configFile = sys.argv[1]
    except IndexError:
        # Try loading config file with same name as python script
        configFile = __file__.rstrip('.py') + '.ini'
        # If no filename is specified and default filename doesn't exist => raise error
        if not os.path.exists(configFile):
            error_msg = "No configuration file specified, please type: python main.py {config filename}.ini"
            raise IOError, error_msg
    # If config file doesn't exist => raise error
    if not os.path.exists(configFile):
        error_msg = "Configuration file '" + configFile +"' not found"
        raise IOError, error_msg

    flStartLog(cnfGetIniValue(configFile, 'Logging', 'LogFile', __file__.rstrip('.py') + '.log'),
               cnfGetIniValue(configFile, 'Logging', 'LogLevel', 'DEBUG'),
               cnfGetIniValue(configFile, 'Logging', 'Verbose', True))

    kdeType = cnfGetIniValue(configFile, 'StatInterface', 'kdeType',
                             'Gaussian')
    gridLimit = eval(cnfGetIniValue(configFile, 'Settings', 'gridLImit'))
    kdeStep = 0.1
    kde = KDEOrigin(configFile, kdeType, gridLimit, kdeStep)
    kde.generateKDE(save=True)

    kde.generateCdf(save=True)
