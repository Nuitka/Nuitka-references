from pypy.rpython.lltypesystem import rffi, lltype
from pypy.module.cpyext.api import (
    PyObjectFields, generic_cpy_call, CONST_STRING,
    cpython_api, bootstrap_function, cpython_struct, build_type_checkers)
from pypy.module.cpyext.pyobject import (
    PyObject, make_ref, from_ref, Py_DecRef, make_typedescr, borrow_from)
from pypy.rlib.unroll import unrolling_iterable
from pypy.interpreter.error import OperationError
from pypy.interpreter.function import Function, Method
from pypy.interpreter.pycode import PyCode
from pypy.interpreter import pycode

CODE_FLAGS = dict(
    CO_OPTIMIZED   = 0x0001,
    CO_NEWLOCALS   = 0x0002,
    CO_VARARGS     = 0x0004,
    CO_VARKEYWORDS = 0x0008,
    CO_NESTED      = 0x0010,
    CO_GENERATOR   = 0x0020,
)
ALL_CODE_FLAGS = unrolling_iterable(CODE_FLAGS.items())

PyFunctionObjectStruct = lltype.ForwardReference()
PyFunctionObject = lltype.Ptr(PyFunctionObjectStruct)
PyFunctionObjectFields = PyObjectFields + \
    (("func_name", PyObject),)
cpython_struct("PyFunctionObject", PyFunctionObjectFields, PyFunctionObjectStruct)

PyCodeObjectStruct = lltype.ForwardReference()
PyCodeObject = lltype.Ptr(PyCodeObjectStruct)
PyCodeObjectFields = PyObjectFields + \
    (("co_name", PyObject),
     ("co_flags", rffi.INT),
     ("co_argcount", rffi.INT),
    )
cpython_struct("PyCodeObject", PyCodeObjectFields, PyCodeObjectStruct)

@bootstrap_function
def init_functionobject(space):
    make_typedescr(Function.typedef,
                   basestruct=PyFunctionObject.TO,
                   attach=function_attach,
                   dealloc=function_dealloc)
    make_typedescr(PyCode.typedef,
                   basestruct=PyCodeObject.TO,
                   attach=code_attach,
                   dealloc=code_dealloc)

PyFunction_Check, PyFunction_CheckExact = build_type_checkers("Function", Function)
PyMethod_Check, PyMethod_CheckExact = build_type_checkers("Method", Method)

def function_attach(space, py_obj, w_obj):
    py_func = rffi.cast(PyFunctionObject, py_obj)
    assert isinstance(w_obj, Function)
    py_func.c_func_name = make_ref(space, space.wrap(w_obj.name))

@cpython_api([PyObject], lltype.Void, external=False)
def function_dealloc(space, py_obj):
    py_func = rffi.cast(PyFunctionObject, py_obj)
    Py_DecRef(space, py_func.c_func_name)
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, py_obj)

def code_attach(space, py_obj, w_obj):
    py_code = rffi.cast(PyCodeObject, py_obj)
    assert isinstance(w_obj, PyCode)
    py_code.c_co_name = make_ref(space, space.wrap(w_obj.co_name))
    co_flags = 0
    for name, value in ALL_CODE_FLAGS:
        if w_obj.co_flags & getattr(pycode, name):
            co_flags |= value
    rffi.setintfield(py_code, 'c_co_flags', co_flags)
    rffi.setintfield(py_code, 'c_co_argcount', w_obj.co_argcount)

@cpython_api([PyObject], lltype.Void, external=False)
def code_dealloc(space, py_obj):
    py_code = rffi.cast(PyCodeObject, py_obj)
    Py_DecRef(space, py_code.c_co_name)
    from pypy.module.cpyext.object import PyObject_dealloc
    PyObject_dealloc(space, py_obj)

@cpython_api([PyObject], PyObject)
def PyFunction_GetCode(space, w_func):
    """Return the code object associated with the function object op."""
    func = space.interp_w(Function, w_func)
    w_code = space.wrap(func.code)
    return borrow_from(w_func, w_code)

@cpython_api([PyObject, PyObject, PyObject], PyObject)
def PyMethod_New(space, w_func, w_self, w_cls):
    """Return a new method object, with func being any callable object; this is the
    function that will be called when the method is called.  If this method should
    be bound to an instance, self should be the instance and class should be the
    class of self, otherwise self should be NULL and class should be the
    class which provides the unbound method."""
    return Method(space, w_func, w_self, w_cls)

@cpython_api([PyObject], PyObject)
def PyMethod_Function(space, w_method):
    """Return the function object associated with the method meth."""
    assert isinstance(w_method, Method)
    return borrow_from(w_method, w_method.w_function)

@cpython_api([PyObject], PyObject)
def PyMethod_Self(space, w_method):
    """Return the instance associated with the method meth if it is bound,
    otherwise return NULL."""
    assert isinstance(w_method, Method)
    return borrow_from(w_method, w_method.w_instance)

@cpython_api([PyObject], PyObject)
def PyMethod_Class(space, w_method):
    """Return the class object from which the method meth was created; if this was
    created from an instance, it will be the class of the instance."""
    assert isinstance(w_method, Method)
    return borrow_from(w_method, w_method.w_class)

@cpython_api([PyObject], PyObject)
def PyClassMethod_New(space, w_function):
    return space.call_method(space.builtin, "classmethod", w_function)

def unwrap_list_of_strings(space, w_list):
    return [space.str_w(w_item) for w_item in space.fixedview(w_list)]

@cpython_api([rffi.INT_real, rffi.INT_real, rffi.INT_real, rffi.INT_real,
              PyObject, PyObject, PyObject, PyObject, PyObject, PyObject,
              PyObject, PyObject, rffi.INT_real, PyObject], PyCodeObject)
def PyCode_New(space, argcount, nlocals, stacksize, flags,
               w_code, w_consts, w_names, w_varnames, w_freevars, w_cellvars,
               w_filename, w_funcname, firstlineno, w_lnotab):
    """Return a new code object.  If you need a dummy code object to
    create a frame, use PyCode_NewEmpty() instead.  Calling
    PyCode_New() directly can bind you to a precise Python
    version since the definition of the bytecode changes often."""
    return space.wrap(PyCode(space,
                             argcount=rffi.cast(lltype.Signed, argcount),
                             nlocals=rffi.cast(lltype.Signed, nlocals),
                             stacksize=rffi.cast(lltype.Signed, stacksize),
                             flags=rffi.cast(lltype.Signed, flags),
                             code=space.str_w(w_code),
                             consts=space.fixedview(w_consts),
                             names=unwrap_list_of_strings(space, w_names),
                             varnames=unwrap_list_of_strings(space, w_varnames),
                             filename=space.str_w(w_filename),
                             name=space.str_w(w_funcname),
                             firstlineno=rffi.cast(lltype.Signed, firstlineno),
                             lnotab=space.str_w(w_lnotab),
                             freevars=unwrap_list_of_strings(space, w_freevars),
                             cellvars=unwrap_list_of_strings(space, w_cellvars)))

@cpython_api([CONST_STRING, CONST_STRING, rffi.INT_real], PyCodeObject)
def PyCode_NewEmpty(space, filename, funcname, firstlineno):
    """Creates a new empty code object with the specified source location."""
    return space.wrap(PyCode(space,
                             argcount=0,
                             nlocals=0,
                             stacksize=0,
                             flags=0,
                             code="",
                             consts=[],
                             names=[],
                             varnames=[],
                             filename=rffi.charp2str(filename),
                             name=rffi.charp2str(funcname),
                             firstlineno=rffi.cast(lltype.Signed, firstlineno),
                             lnotab="",
                             freevars=[],
                             cellvars=[]))

