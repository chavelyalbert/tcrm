"""
:mod:`trackSize` -- determine radius to max winds
=================================================

.. module:: trackSize
    :synopsis: Determine the radius to maximum winds for each cyclone
               using either statistics from observations or a
               parametric model based on latitude and central pressure
               deficit.
.. moduleauthor:: Craig Arthur, <craig.arthur@ga.gov.au>

"""

import numpy as np
import logging
import scipy.stats as stats
import statsmodels.api as sm

LOG = logging.getLogger()

def rmax(dp, lat, eps, coeffs=[4.4726049824584306, 
                               -0.04057322103602546, 
                               0.00031318220949448573, 
                               0.00014553984831170656]):
    """
    Calculate radius to maximum wind based on pressure deficit and
    latitude. This function allows for the random variate to be set
    when calling the function. Default coefficients for the functional
    form of ln(Rmw) are given.
    
    ln(Rmw) = a + b*dp + c*dp^2 + d*lat^2 + eps

    eps is not included in the coefficients (though that may be considered
    by some to be more logical), so that it can remain constant for a single
    TC event. 

    :param dp: Central pressure deficit (hPa)
    :param lat: Latitude of the storm (degrees)
    :param eps: random variate. This would normally be held constant
                for a single storm.
    :param coeffs: A list of coefficients for the functional form. Default
                   values are based on JTWC data from the southern hemisphere.

    :returns: radius to maximum wind value.

    """
    if len(coeffs) < 4:
        LOG.warn("Insufficient coefficients for rmw calculation!")
        LOG.warn("Using default values")
        coeffs = [4.4726049824584306, 
                  -0.04057322103602546, 
                  0.00031318220949448573, 
                  0.00014553984831170656]

    if isinstance(dp, (np.ndarray, list)) and \
      isinstance(lat, (np.ndarray, list)):
        assert len(dp) == len(lat)
    rm = np.exp(coeffs[0] + coeffs[1] * dp + coeffs[2] * dp * dp +
                coeffs[3] * lat * lat + eps)
      
    return rm

def fitRmax(rmw, dp, lat):
    """
    Fit Rmw data to a function of pressure deficit and latitude.

    We fit a function of dp and latitude to ln(Rmw) values of the
    form:

    ln(Rmw) = a + b*dp + c*dp^2 + d*lat^2 + eps

    where eps is a random normal variate with zero mean and std. dev.
    describing the residual variance. 

    :param rmw: :class:`numpy.ndarray` of valid Rmw observations.
    :param dp: :class:`numpy.ndarray` of valid pressure deficit.
               observations, corresponding to the Rmw observations.
    :param lat: :class:`numpy.ndarray` of latitude observations for
                the Rmw observations.

    :returns: list of coefficients for the functional form and a
              std dev for the random variate.

    """

    assert len(dp) == len(lat)
    assert len(rmw) == len(dp)
    
    X = np.column_stack((dp, dp*dp, lat*lat))
    X = sm.add_constant(X)
    y = np.array(np.log(rmw))
    model = sm.OLS(y, X)
    results = model.fit()
    params = list(results.params)

    r = results.resid
    rf = stats.norm.fit(r, shape=np.mean(r), scale=np.std(r))

    params.append(rf[1])
    return params