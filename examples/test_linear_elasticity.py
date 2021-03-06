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
import math
import numpy as np

from dolfin import *
from FenicsSolver import LinearElasticitySolver
from FenicsSolver import SolverBase
set_log_level(ERROR)

from config import is_interactive
interactively = is_interactive()

def test(has_thermal_stress, has_body_source, transient = False, boundary_type = 1):
    #has_body_source to test gravity as body source
    #
    xmin, xmax = 0, 10
    ymin, ymax = 0, 1
    zmin, zmax = 0, 1
    nx,ny,nz = 40, 10, 10
    mesh = BoxMesh(Point(xmin, ymin, zmin), Point(xmax, ymax,zmax), nx,ny,nz)
    geo_dim = mesh.geometry().dim()

    ####################################
    # Left boundary 
    class Left(SubDomain):
        def inside(self, x, on_boundary):
            return near(x[0], xmin)

    # Right boundary
    class Right(SubDomain):
        def inside(self, x, on_boundary):
            return near(x[0], xmax)

    top = AutoSubDomain(lambda x, on_boundary: on_boundary and near(x[1], ymax) )
    bottom = AutoSubDomain(lambda x, on_boundary: on_boundary and near(x[1], ymin) )
    # Point (8,0.5,0.5) at which load is added
    #DirichletBC(V, g_T, pt, method="pointwise")] 
    class point(SubDomain):
        def inside(self, x, on_boundary):
            return near(x[0], xmax) and near(x[1],0.5,1e-2) and near(x[2],0.5,1e-2)

    omega = 100 # rad/s, axis, origin are other parameters
    rho = 7800 # kg/m3, density
    # body force: Loading due to centripetal acceleration (rho*omega^2*x_i) or gravity
    #bf = Expression(("rho*omega*omega*x[0]", "rho*omega*omega*x[1]", "0.0"), omega=omega, rho=rho, degree=2)
    bf = Expression(("10*rho", "0", "0.0"), omega=omega, rho=rho, degree=2)  # gravity but in x-axis

    from collections import OrderedDict
    bcs = OrderedDict()
    #
    #bcs["fixed"] = {'boundary': Left(), 'boundary_id': 1, 'type': 'Dirichlet', 'value': Constant((0,0,0))}
    bcs["fixed"] = {'boundary': Left(), 'boundary_id': 1, 'type': 'Dirichlet', 'value': (Constant(0), None, None)}

    if boundary_type == 1:
        bcs["displ"] = {'boundary': Right(), 'boundary_id': 2, 'type': 'Dirichlet', 'value': Constant((0, 0, zmax*1e-3))}
        #bcs["displ"] = {'boundary': Right(), 'boundary_id': 2, 'type': 'Dirichlet', 'value': (Constant(0), None, None)}
        # constraint only one direction displacement
        #bcs["displ"] = {'boundary': Right(), 'boundary_id': 2, 'type': 'Dirichlet', 'value': (None, None, Constant(0.01))}
    elif boundary_type == 2:
        bcs["tensile"] = {'boundary': Right(), 'boundary_id': 2, 'type': 'stress', 'value': Constant((1e8,0, 0))}  #correct, normal stress
        # force on boundary surface is converted into tangential and normal stress and apply onto boundary facets
        #bcs["pressing"] = {'boundary': top, 'boundary_id': 3, 'type': 'stress', 'value': Constant((0, 1e6, 0)), 'direction': None}        
    elif boundary_type == 3:
        bcs["bending"] = {'boundary': Right(), 'boundary_id': 2, 'type': 'force', 'value': Constant((0, 1e6, 0))} # correct, shearing force
    else:
        raise NotImplementedError()

    # TODO:
    #bcs["sym"] = {'boundary': bottom, 'boundary_id': 4, 'type': 'symmetry', 'value': None}
    #bcs["antisym"] = {'boundary': bottom, 'boundary_id': 4, 'type': 'antisymmetry', 'value': None}

    # TODO: spring is an analog to heat transfer coefficient 
    #bcs["spring"] = {'boundary': bottom, 'boundary_id': 4, 'type': 'spring',
    #                            'K':  Constant(), 'fixed_position': Point(xmax,4,(zmin+xmax)*0.5))}
    # for dynamic system, damping boundary

    dt = 0.001
    f =100
    t_end = 0.005
    transient_settings = {'transient': True, 'starting_time': 0.0, 'time_step': dt, 'ending_time': t_end}

    # Create function space
    fe_degree = 2
    V = VectorFunctionSpace(mesh, "Lagrange", fe_degree)
    #external Temperature distribution can be solved by the same function space, then pass to elastic solver

    import copy
    s = copy.copy(SolverBase.default_case_settings)  # deep copy? 
    s['material'] = {'name': 'steel', 'elastic_modulus': 2e11, 'poisson_ratio': 0.27, 'density': 7800, 
                                'thermal_expansion_coefficient': 2e-6} #default to steel
    s['function_space'] = V
    s['boundary_conditions'] = bcs
    s['temperature_distribution']=None
    #s['vector_name'] = 'displacement'
    s['solver_settings']['reference_values'] = {'temperature':293 }  # solver specific setting
    if transient:
        s['solver_settings']['transient_settings'] = transient_settings
        dynamic_stress = lambda t:  Constant((1e8*math.sin(f*math.pi*2*t), 0, 0))
        bcs["tensile"] = {'boundary': Right(), 'boundary_id': 2, 'type': 'stress', 'value': dynamic_stress}  #correct, normal stress

    if has_thermal_stress:
        print('test thermal stress')
        s['temperature_distribution'] = Expression("343", degree=fe_degree)
        #Expression("dT * x[1]/ymax", dT = 100, ymax=ymax, degree=fe_degree)
        # need a better expression to test thermal. 
    if has_body_source:
        s['body_source'] = bf
    solver = LinearElasticitySolver.LinearElasticitySolver(s)  # body force test passed

    '''
    X0 = FunctionSpace(mesh, "RT", 2)
    X = VectorFunctionSpace(mesh, "RT", 2)
    u = interpolate(Expression(('1', '2')), X0)
    project(grad(u), X)
    '''

    #ev = solver.solve_modal()  # need proper boundary condition to test?
    u = solver.solve()
    plot(solver.von_Mises(u), title='Stress von Mises')
    #if not run by pytest
    if interactively:
        solver.plot()

    ###################################
    if False:
        # Save solution to VTK format
        File("elastic_displacement.pvd", "compressed") << u

        # Save colored mesh partitions in VTK format if running in parallel
        if MPI.size(mesh.mpi_comm()) > 1:
            File("partitions.pvd") << CellFunction("size_t", mesh, \
                                                   MPI.rank(mesh.mpi_comm()))

        # Project and write stress field to post-processing file
        W = TensorFunctionSpace(mesh, "Discontinuous Lagrange", 0)
        stress = project(solver.sigma(u), V=W)
        File("stress.pvd") << stress
    #####################################

if __name__ == '__main__':
    #test(has_thermal_stress = True, has_body_source=True, transient = False, boundary_type =2)
    test(has_thermal_stress = True, has_body_source=True, transient = True)
    test(has_thermal_stress = True, has_body_source=True)
    test(has_thermal_stress = False, has_body_source=True)
    test(has_thermal_stress = True, has_body_source=False)
    test(has_thermal_stress = False, has_body_source=False)