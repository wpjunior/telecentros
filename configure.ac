#  Copyright (C) 2011 <wilsonpjunior@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

AC_INIT([TeleCentros Client],[0.1],[http://www.lethus.com.br],[telecentros])
AM_CONFIG_HEADER(config.h)
AM_INIT_AUTOMAKE([1.7])
AM_MAINTAINER_MODE
AC_PROG_CC

AC_DEFUN([AC_DEFINE_PATH], [
    test "x$prefix" = xNONE && prefix="$ac_default_prefix"
    test "x$exec_prefix" = xNONE && exec_prefix='${prefix}'
    ac_define_path=`eval echo [$]$2`
    ac_define_path=`eval echo [$]ac_define_path`
    $1="$ac_define_path"
    AC_SUBST($1)
    ifelse($3, ,
        AC_DEFINE_UNQUOTED($1, "$ac_define_path"),
        AC_DEFINE_UNQUOTED($1, "$ac_define_path", $3))
    ])

GETTEXT_PACKAGE=telecentros
AC_SUBST([GETTEXT_PACKAGE])
AC_DEFINE_UNQUOTED([GETTEXT_PACKAGE],["$GETTEXT_PACKAGE"],[Gettext package])
AC_DEFINE_PATH(GNOMELOCALEDIR, "${datadir}/locale", [locale directory])
AC_DEFINE_PATH(DATADIR, "${datadir}", [datadir directory])
AC_PROG_INTLTOOL([0.35.0])
AM_GLIB_GNU_GETTEXT
AM_GCONF_SOURCE_2
AM_PROG_LIBTOOL

AC_PATH_PROG(GCONFTOOL, gconftool-2, no)

dnl python checks
AM_PATH_PYTHON(2.7)

PY_PREFIX=`$PYTHON -c 'import sys ; print sys.prefix'`
PYTHON_LIBS="-lpython$PYTHON_VERSION"
PYTHON_CFLAGS="-I$PY_PREFIX/include/python$PYTHON_VERSION"

AC_SUBST([PYTHON_LIBS])
AC_SUBST([PYTHON_CFLAGS])

#PyGDM
dnl Checking G* Libraries
PKG_CHECK_MODULES(PYGDM,
    glib-2.0
    gdk-2.0
)

AC_SUBST(PYGDM_CFLAGS)
AC_SUBST(PYGDM_LIBS)

dnl gtk dependencie
PYGTK_REQUIRED=2.12.0

PKG_CHECK_MODULES([DEPENDENCIES], [
    pygtk-2.0 >= $PYGTK_REQUIRED
])


dnl output files
AC_CONFIG_FILES([
Makefile
data/Makefile
data/telecentros.desktop.in
data/ui/Makefile
data/icons/Makefile
src/Makefile
src/TeleCentros/Makefile
src/pygdm/Makefile
src/TeleCentros/ui/Makefile
src/TeleCentros/config.py
po/Makefile.in
])

AC_OUTPUT

echo "
telecentros-$VERSION:

	prefix:                 ${prefix}

"
