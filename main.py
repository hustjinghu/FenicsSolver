# -*- coding: utf-8 -*-
# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2017 - Qingfeng Xia <qingfeng.xia eng ox ac uk>                 *       *
# *                                                                         *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License (LGPL)    *
# *   as published by the Free Software Foundation; either version 2 of     *
# *   the License, or (at your option) any later version.                   *
# *   for detail see the LICENCE text file.                                 *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Library General Public License for more details.                  *
# *                                                                         *
# *   You should have received a copy of the GNU Library General Public     *
# *   License along with this program; if not, write to the Free Software   *
# *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
# *   USA                                                                   *
# *                                                                         *
# ***************************************************************************

from __future__ import print_function, division
import json
import sys
import os.path

import ScalerEquationSolver
import CoupledNavierStokesSolver

"To cope with different python versions for FreeCAD and Fenics, running as an external program"


_encoding = 'ascii'
def _decode_list(data):
    rv = []
    for item in data:
        if isinstance(item, unicode):
            item = item.encode(_encoding)
        elif isinstance(item, list):
            item = _decode_list(item)
        elif isinstance(item, dict):
            item = _decode_dict(item)
        rv.append(item)
    return rv

def _decode_dict(data):
    rv = {}
    for key, value in data.iteritems():
        if isinstance(key, unicode):
            key = key.encode(_encoding)
        if isinstance(value, unicode):
            value = value.encode(_encoding)
        elif isinstance(value, list):
            value = _decode_list(value)
        elif isinstance(value, dict):
            value = _decode_dict(value)
        rv[key] = value
    return rv
#obj = json.loads(s, object_hook=_decode_dict)


def main(case_input):
    # Order of key in dict is lost
    if isinstance(case_input, (dict)):
        settings = case_input
    elif isinstance(case_input, (unicode, str)):
        s = open(case_input, 'r').read()
        settings = json.loads(s, object_hook=_decode_dict)
    else:
        raise TypeError('{} is not supported by Fenics as case input, only path string or dict'.format(type(case_input)))

    solver_name = settings['solver_name']
    if solver_name == "CoupledNavierStokesSolver":
        solver = CoupledNavierStokesSolver.CoupledNavierStokesSolver(settings)
        solver.solve()
    elif solver_name == "ScalerEquationSolver":
        solver = ScalerEquationSolver.ScalerEquationSolver(settings)
        solver.solve()
    else:
        raise NameError('Solver name : {} is not supported by Fenics'.format(solver_name))
    #plot may be done by ParaView or by fenics solver.plot()
    solver.plot()

def test_elasticity():
    pass

def test_CFD():
    #df = open(os.path.dirname(__file__) + os.path.sep + 'data/TestCFD.json', 'r')
    df = open('./data/TestCFD.json', 'r')
    settings = json.loads(df.read(), object_hook=_decode_dict)  # force python2 load ascii string
    #settings['case_folder'] = os.path.dirname(__file__) + os.path.sep + "data"
    solver = CoupledNavierStokesSolver.CoupledNavierStokesSolver(settings)
    solver.print()
    solver.solve()
    solver.plot()

def test_heat_transfer():
    #print(os.path.dirname(__file__))  # __file__ is absolute path for python 3.4+
    df = open('./data/TestHeatTransfer.json', 'r')
    settings = json.loads(df.read(), object_hook=_decode_dict)  # force python2 load ascii string
    #settings['case_folder'] = os.path.dirname(__file__) + os.path.sep + "data"
    solver = ScalerEquationSolver.ScalerEquationSolver(settings)
    solver.print()
    solver.solve()
    solver.plot()

if __name__ == "__main__":
    # will mpirun also affect argv? No, the first is always the one following `python`, i.e. `main.py`
    print(sys.argv)
    if len(sys.argv) < 2:

        print("Not enough input argument, Usage: `python main.py case_input` \n run testing instead")
        #  must start this solver in FenicsSolver folder

        test_heat_transfer()
        #test_CFD()  # not converging
    else:
        main(sys.argv[1])