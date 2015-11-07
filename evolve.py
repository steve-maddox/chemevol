from scipy.integrate import quad
import functions as f
import numpy as np
from lookups import find_nearest, lifetime_lookup, t_lifetime
import logging

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('chem')


class ChemModel:
    def __init__(self, **inputs):
        #f.validate_initial_dict(inputs)
        try:
            self.gasmass_init = inputs['gasmass_init']
            self.gamma = inputs['gamma']
            self.imf_type = inputs['IMF_fn']
            self.dust_source = inputs['dust_source']
            self.destroy = inputs['destroy']
            self.inflows = inputs['inflows']
            self.outflows = inputs['outflows']
            self.SFH_file = inputs['SFH']
            if not self.SFH_file:
                self.SFH_file = 'Milkyway.sfh'
            self.sfh_file = self.SFH_file
            self.load_sfh()
        except KeyError:
            logger.error('You must provide initial parameters')

    def load_sfh(self):
        try:
            vals = np.loadtxt(self.SFH_file)
            scale = [1./1e9,1e9] # this puts time in Gyr and SFR in Msun/Gyr 
            self.sfh = vals*scale
        except:
            logger.error("File '%s' will not parse" % self.SFH_file)
            self.sfh = None

    def sfr(self, t):
        try:
            vals = find_nearest(self.sfh,t)
            return vals[1]
        except:
            logger.error("No SFH yet")
            
    def final_sfr(self, t):
        try:
            vals = find_nearest(self.extra_sfr,t)
            return vals[1]
        except:
            logger.error("No SFH yet")      

    def ejected_mass(self, t):
        mu = t_lifetime[-1][0]
        m = lifetime_lookup(t_lifetime,'lifetime_low_metals',t)[0]
        dm = 0.5
        em = 0.
        while m <= mu:
            em += f.ejected_gas_mass(m, self.sfr(t), self.imf_type) * dm
            m += dm
        return em
    
    def extra_sfr(self):
        '''
        This extrapolates the SFH provided to start at 0.001Gyr
        with 100 extra steps between 0.001Gyr and the first non-zero
        entry in the SFH list.
        
        Returns a new SFH list made from joining the
        extrapolated SFH in this routine to the original input SFH file
        '''
        #to start integral at t_0 regardless of when SFH file starts 
        t_0 = 1e-3 # we want it to start at 1e-3
        tend_sfh = self.sfh[1][0] # 1st time array after 0
        # work out difference between t_0 and [1] entry in SFH
        dlogt = (np.log10(tend_sfh) - np.log10(t_0))/100
        norm = self.sfh[1][1]*(1./np.exp(-1.*self.gamma*tend_sfh))
        sfr_extra = norm * np.exp(-1.*self.gamma*t_0)
        sfr_new = sfr_extra
        t_new = t_0
        n = 0
        newlist = []
        #create new array between 0.001 Gyr and start of SFH data 
        while t_new < tend_sfh:
            t_new = 10.**(np.log10(t_new)+dlogt)
            sfr_new = norm * np.exp(-1.*self.gamma*t_new)
            n += 1
            newlist.append([t_new,sfr_new])    
        # start from [2:] to account for t[0],t[1] repeated entries 
        # when new and in old SFHs combined    
        final_sfh = newlist + (self.sfh.tolist()[2:])
#        return final_sfh 

    def gas_mass(self):
        mg = self.gasmass_init
        print self.sfh[:,0]
        for t in self.sfh[:,0]:
            dmg = - self.sfr(t) + self.ejected_mass(t) + f.inflows(self.sfr(t), \
                self.inflows).value + f.outflows(self.sfr(t), self.outflows).value
            dt = self.sfh[:,0]-self.sfh[:,0]
            mg += dmg*dt
            print t, mg, dt
        return mg   
        
        #this doesnt work anymore -- need to edit for sfh file too



