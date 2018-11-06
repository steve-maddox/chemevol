'''
Chemevol - Python package to read in a star formation history file,
input galaxy parameters and run a chemical evolution model to determine the evolution
of gas, metals and dust in galaxies.

Running this script will produce a results data file (filename.dat) with file name given by user

The code is based on Morgan & Edmunds 2003 (MNRAS, 343, 427)
and described in detail in Rowlands et al 2014 (MNRAS, 441, 1040).

If you use this code, please do cite the above papers.

Copyright (C) 2015 Haley Gomez, Edward Gomez and Simon Schofield, Cardiff University and LCOGT.
The code has been contributed by Pieter De Vis and Kate Rowlands.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

********************************************************************************
'''

from .functions import extra_sfh, astration, remnant_mass, imf_chab, imf_topchab, \
    imf_salp, imf_kroup, initial_mass_function, initial_mass_function_integral, \
    ejected_gas_mass, fresh_metals, lookup_fn, lookup_taum, mass_integral, mass_yields, \
    inflows, remnant_mass, t_lifetime, t_yields, graingrowth, destroy_dust, \
    gas_inandout, metals_inandout, dust_inandout, outflows_feldmann, oxymass_yields

from astropy.table import Table
import numpy as np
from numpy import array
from .lookups import find_nearest, lookup_fn, t_lifetime, lookup_taum
import logging
from datetime import datetime
import os.path
import json

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger('chem')

class ChemModel:
    def __init__(self, **inputs):
        '''
        set initial parameters from input dictionary and sort out choices
        for IMF, dust source
        '''
        #f.validate_initial_dict(inputs)
        try:
            self.gasmass_init = inputs['gasmass_init']
            self.gamma = inputs['gamma']
            self.tend = inputs['t_end']
            self.imf_type = inputs['IMF_fn']
            self.dust_source = inputs['dust_source']
            self.delta_lims = inputs['delta_lims_fresh']
            self.reduce_sn = inputs['reduce_sn_dust']
            self.destroy = inputs['destroy']
            self.inflows = inputs['inflows']
            self.outflows = inputs['outflows']
            self.SFH_file = inputs['SFH']
            self.coldfraction = inputs['cold_gas_fraction']
            self.availablefraction = inputs['available_metal_fraction']
            self.eff_snrate = inputs['effective_snrate_factor']
            self.epsilon = inputs['epsilon_grain']
            # check for SFH file or use Milkway.sfh provided
            if not self.SFH_file:
                self.SFH_file = 'chemevol/Milkyway.sfh'
            self.sfh_file = self.SFH_file
            self.load_sfh()
        except KeyError:
            logger.error('You must provide initial parameters in the correct format')
        # Set up IMF Function determined by user, allow for variety of spellings
        if (self.imf_type in ["Chab", "chab", "c"]):
            self.imf = imf_chab
        elif (self.imf_type in ["TopChab", "topchab","tc"]):
            self.imf = imf_topchab
        elif (self.imf_type in ["Kroup", "kroup", "k"]):
            self.imf = imf_kroup
        elif (self.imf_type in ["Salp", "salp", "s"]):
            self.imf = imf_salp
        if not self.reduce_sn['on'] or self.reduce_sn['factor'] == 0:
            self.reduce_sn = 1
        else:
            self.reduce_sn = self.reduce_sn['factor']
        # set up dust source choice from user: sn = True; SN dust on, lims = True; LIMS dust on, gg = Grain Growth
        if self.dust_source in ["ALL", "all", "All"]:
            self.choice_dust = {
                                    'sn' : True,
                                    'lims' : True,
                                    'gg' :True
                                }
        elif self.dust_source in ["SN", "Sn", "sn"]:
            self.choice_dust =  {
                                    'sn' : True,
                                    'lims' : False,
                                    'gg' :False
                                }
        elif self.dust_source in ["LIMS", "Lims", "lims"]:
            self.choice_dust =  {
                                    'sn' : False,
                                    'lims' : True,
                                    'gg' :False
                                }
        elif self.dust_source in ["SN+LIMS", "sn+lims", "LIMS+SN", "lims+sn"]:
            self.choice_dust =  {
                                    'sn' : True,
                                    'lims' : True,
                                    'gg' :False
                                }
        else:
            print ('oops please check the dust sources are in the right format and try again')
            exit()

    def load_sfh(self):
        '''
        takes in input SFH file and extend backwards to start from 1e-3 Gyr
        '''
        try:
            vals = np.loadtxt(self.SFH_file)
            scale = [1e-9,1e9] # Gyr conversions for time, SFR (because we want to do dt integral over Gyrs)
            sfh = vals*scale # converts time in Gyr and SFR in Msun/Gyr
            # extrapolates SFH back to 0.001Gyr using SFH file and power law (gamma)
            final_sfh = extra_sfh(sfh, self.gamma)
            self.sfh = np.array(final_sfh)
        except Exception as e:
            logger.error("File '%s' will not parse %s" % (self.SFH_file, e))
            self.sfh = None

    def sfr(self, t):
        '''
        define sfr as function to look up nearest sfr value at any specified time
        '''
        try:
            vals = find_nearest(self.sfh,t)
            return vals[1]
        except:
            logger.error("No SFH yet")

    def gas_metal_dust_mass(self, sn_rate):
            '''
            Calculates the gas, metal and dust mass from stars
            note mass is only ejected after stars die ie when
            t - taum (where taum is lifetime of star) > 0
            '''
            # initialize
            mg = self.gasmass_init
            mstars = 0
            md = 0
            md_all = 0
            md_stars = 0
            md_gg = 0
            metals = 0
            prev_t = 1e-3
            metals_pre = 0
            mstars_list = []
            z = []
            z_lookup = []
            sfr_list = []
            sfr_lookup = []
            all_results = []
            oxymass = 0
            oxymass_pre = 0
            oxymass_pre = 0
            oxyz =[]
            oxy_lookup = []
            # Limit time to less than tend
            time = self.sfh[:,0] # sfr is in units of Msun Gyr^-1
            time = time[time < self.tend]
            now = datetime.now()

            # TIME integral
            for item, t in enumerate(time):
                r_sn = sn_rate [item]
                metallicity = metals/mg
                oxy_metallicity = oxymass/mg
                # start appending arrays for needing later
                z.append([t,metallicity])
                z_lookup = array(z)
                oxyz.append([t,oxy_metallicity])
                oxy_lookup= array(oxyz)
                sfr_list.append([t,self.sfr(t)])
                sfr_lookup = array(sfr_list)

                # Now for setting up the components of the integrals
                # Stars, gas and dust
                '''
                GAS: dMg = (-sfr(t) + e(t) + inflows(t) - outflows(t)) * dt
                set up astration, inflow, outflow components
                '''
                gas_ast = self.sfr(t) # gas lost due to astration
                # How much gas is lost or gained dure to outflows/inflows
                gas_inf,gas_out = gas_inandout(
                    self.inflows['on'],\
                    self.outflows['on'],\
                    self.inflows['xSFR'],\
                    self.sfr(t),\
                    mstars)
            #    print 'time=',t,'sfr=',self.sfr(t)/1e9,'mstar=',mstars/1e10,'gas=','dust=',md_all/1e6,gas_out,gas_inf

                '''
                METALS: dMz = (-Z*sfr(t) + ez(t) + Z*inflows(t) - Z*outflows(t)) * dt
                set up astration, inflow and outflow components
                '''
                # metals lost due to astration
                metals_ast = astration(metals,mg,self.sfr(t))
                # do oxygen metals so we can have 12+log(O/H) later
                oxymass_ast = astration(oxymass,mg,self.sfr(t))
                # are outflows and inflows on (True) and if so what metal parameters needed?
                oxy_metal_inflow = 0.64*self.inflows['metals'] # fraction of total metals made up of oxygen
                metals_inf,metals_out,oxymass_inf,oxymass_out = metals_inandout(
                    self.inflows['on'],\
                    self.inflows['xSFR'],\
                    self.inflows['metals'],\
                    self.outflows['on'],\
                    self.outflows['metals'],\
                    self.sfr(t),\
                    metallicity,\
                    oxy_metallicity,\
                    oxy_metal_inflow,\
                    mstars)
                '''
                DUST: dMd = (-Md/Mg*sfr(t) + ed(t) + Md/Mg*inflows(t) - Md/Mg*outflows(t)
                             - (1-f)*Md/t_destroy + f(1-Md/Mg)*Md/t_graingrowth) * dt
                set up astration, inflows, outflows, destruction, grain growth components
                '''
                # are outflows and inflows on (True) and if so what dust parameters needed?

                mdust_inf,mdust_out = dust_inandout(
                    self.inflows['on'],\
                    self.inflows['xSFR'],\
                    self.inflows['dust'],\
                    self.outflows['on'],\
                    self.outflows['dust'],\
                    self.sfr(t),\
                    (md/mg),
                    mstars)

                mdust_ast = astration(md,mg,self.sfr(t))

                mdust_gg, t_gg = graingrowth(self.choice_dust['gg'],self.epsilon,mg, self.sfr(t), \
                    metallicity, md, self.coldfraction, self.availablefraction)
                mdust_des, t_des = destroy_dust(self.destroy['on'], self.destroy['mass'], mg, r_sn, \
                    md, self.coldfraction , self.eff_snrate)
                '''
                Get ejected masses from stars when they die
                gas_ej = e(t): ejected gas mass from stars of mass m at t = taum
                metals_stars = ez(t): ejected metal mass from stars of mass m at t = taum (fresh + recycled)
                mdust_stars = ed(t): ejected dust mass from stars of mass m at t = taum (fresh + recycled)
                '''
                gas_ej, metals_stars, oxymass_stars, mdust_stars = \
                        mass_integral(self.choice_dust, self.delta_lims, self.reduce_sn, t, metallicity, sfr_lookup, z_lookup, oxy_lookup, self.imf)

                '''
                STARS: dM_stars = (sfr(t) - e(t) ) * dt
                '''
                dmstars = self.sfr(t) - gas_ej

                '''
                integrate over time for gas, metals and stars (mg, metals, md)
                all time units should be in Gyr or per Gyr
                '''
                dmg = -gas_ast + gas_ej + gas_inf - gas_out
                dmetals = -metals_ast + metals_stars + metals_pre + metals_inf - metals_out
                doxymass = -oxymass_ast + oxymass_stars + oxymass_pre + oxymass_inf - oxymass_out
                ddust = -mdust_ast + mdust_stars + mdust_inf - mdust_out + mdust_gg - mdust_des
                # dust_source_all separates out the dust sources (Md vs t) wihtout including sinks (Astration etc)
                # and grain growth separately (this is the Md vs time contributed by dust sources)
                dust_source_all = mdust_stars + mdust_gg
                dt = t - prev_t             # calculate  next time step
                prev_t = t
                mstars += dmstars*dt
                mg += dmg*dt # gas mass integral
                if mg <= 0:
                    # exit program if all ISM removed
                    print ('Oops you have no interstellar medium left')
                    break
                metals += dmetals*dt # metal mass integral
                oxymass += doxymass*dt # oxygen mass integral
                md += ddust*dt # dust mass integral
                md_all += dust_source_all*dt # dust mass sources integral
                md_gg += mdust_gg*dt # dust source from grain growth only
                md_stars += mdust_stars*dt # dust source from stars only
                Z = zip(*z_lookup) # write metallicity to an array
                s_f_r = zip(*sfr_lookup) # write SFR lookup array
                if mg <= 0. or metals <=0:  # write dust/metals ratio
                    dust_to_metals = 0.
                else:
                    dust_to_metals = md/metals
                all_results.append((t, mg, mstars, metals, metallicity, \
                                    md, dust_to_metals, self.sfr(t)*1e-9, \
                                    md_all, md_stars, md_gg, t_des, t_gg, oxymass))
            print("Gas, metal and dust mass exterior loop %s" % str(datetime.now()-now))
            return np.array(all_results)

    def supernova_rate(self):
        '''
        Calculates the SN rate at time t by integrating over mass m
        '''
        # initialize
        sn_rate_list = []
        dm = 0.01
        prev_t = 1e-3
        # define time array
        time = self.sfh[:,0] # this is in units of Gyrs
        time = time[time < self.tend]
        for t in time:

            # need to clear the sn_rates as we don't want them adding up
            sn_rate = 0.
            dsn_rate = 0.
            if t < 0.049:
                m = lookup_fn(t_lifetime,'lifetime_high_metals',t)[0]

            else:
                m = 9.
            while m < 40.:
                if m > 10.:
                    dm = 0.5
                sn_rate += initial_mass_function(m, self.imf_type)*dm
                m += dm
            r_sn = self.sfr(t)*sn_rate # this is in units of Msun Gyr^-1 x Msun --> Gyr^-1
            dt = t - prev_t
            prev_t = t
            sn_rate_list.append(r_sn) # roughly is ~10 per century at early times and <1 per century at late time
        return np.array(sn_rate_list)

class BulkEvolve:
    def __init__(self, filename):
        if os.path.isfile(filename):
            self.filename = filename
        else:
            logger.error('File {} does not exist'.format(filename))
        return

    def upload_json(self):
        try:
            with open(self.filename) as data_file:
                data = json.load(data_file)
            self.inits = data
        except ValueError:
            logger.error('Cannot read: Are you sure this is a JSON file?')
        return

    def upload_csv(self):
        names = ['name', 'gasmass_init', 'SFH', 't_end', 'gamma', 'IMF_fn', 'dust_source','delta_lims_fresh', \
         'reduce_sn_dust_on', 'reduce_sn_dust_factor','destroy_on', 'mass_destroy', 'inflows_on', 'inflows_metals', 'inflows_xSFR', \
         'inflows_dust', 'outflows_on','outflows_metals', 'outflows_dust', 'cold_gas_fraction', 'available_metal_fraction', \
         'effective_snrate_factor', 'epsilon_grain']
        alttype = np.dtype([('f0','S10'), ('f1', '<f8'), ('f2', 'S30'), ('f3','<f8'),
                    ('f4','<f8'), ('f5','S10'), ('f6','S10'),('f7','<f8'),('f8','bool'), ('f9','<f8'),
                    ('f10','bool'), ('f11','<f8'), ('f12','bool'), ('f13','<f8'),('f14','<f8'),('f15','<f8'),
                    ('f16','bool'), ('f17','bool'),('f18','bool'), ('f19','<f8'), ('f20','<f8'), ('f21','<f8'), ('f22','<f8')])
        try:
            data = np.genfromtxt(self.filename, dtype=alttype,delimiter=',', autostrip=True, names=names)
        except ValueError:
            logger.error('Cannot read: Are you sure this is a CSV file?')
        init_list = []

        for i in range(0,len(data)):
            gal_tup = zip(names, data[i])
            gal_data = dict(gal_tup)
            gal_data['reduce_sn_dust'] = {'on': gal_data['reduce_sn_dust_on'],
                                          'factor': gal_data['reduce_sn_dust_factor']}
            gal_data['inflows'] = { 'on': gal_data['inflows_on'],
                                    'metals': gal_data['inflows_metals'],
                                    'xSFR': gal_data['inflows_xSFR'],
                                    'dust': gal_data['inflows_dust']}
            gal_data['outflows'] = {'on': gal_data['outflows_on'],
                                    'metals': gal_data['outflows_metals'],
                                    'dust': gal_data['outflows_dust']}
            gal_data['destroy'] = {'on': gal_data['destroy_on'],
                                    'mass': gal_data['mass_destroy']}
            init_list.append(gal_data)
        self.inits = init_list
        return


    def evolve_all(self):
        '''
        call modules to run the model:
        snrate:         SN rate at each time step - this also sets time array
                        so ch.supernova_rate() must be called first to set
                        time array for the entire code

        all results:     t, mg, m*, mz, Z, md, md/mz, sfr,
                        dust_source(all), dust_source(stars),
                        dust_source(ism), destruction_time, graingrowth_time,\
						oxygenmass (12+log(O/H))
        '''
        snrate = []
        all_results = []
        galaxies = []

        for item in self.inits:
            logger.warning('Starting run on {}'.format(item['name']))
            ch = ChemModel(**item)

            snrate = ch.supernova_rate()
            all_results = ch.gas_metal_dust_mass(snrate)
            # write all the parameters to a dictionary for each init set
            params = {'time' : all_results[:,0],
                   'mgas' : all_results[:,1],
                   'mstars' : all_results[:,2],
                   'metalmass' : all_results[:,3],
                   'metallicity' : all_results[:,4],
                   'dustmass' : all_results[:,5],
                   'dust_metals_ratio' : all_results[:,6],
                   'sfr' : all_results[:,7],
                   'dust_all' : all_results[:,8],
                   'dust_stars' : all_results[:,9],
                   'dust_ism' : all_results[:,10],
                   'time_destroy' : all_results[:,11],
                   'time_gg' : all_results[:,12],
                   'oxygenmass' : all_results[:,13]}
            params['fg'] = params['mgas']/(params['mgas']+params['mstars'])
            params['ssfr'] = params['sfr']/params['mgas']
            # write to astropy table
            t = Table(params)
            # write out to file based on 'name' identifier
            name = item['name']
            t.write(str(name+'.dat'), format='ascii', delimiter=' ')
            # if you want an array including every inits entry:
            galaxies.append(params)
        self.results = galaxies
        return
