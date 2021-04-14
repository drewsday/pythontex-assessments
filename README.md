# pythontex-assessments
Physics assessments randomized with PythonTex

### Requirements
All of the assessments that are here are making use of the [pythontex package](https://github.com/gpoore/pythontex). In order to typset the documents you will need to have ``python``, a local TeX installation, and ``pythontex`` installed. If you already have a local TeX installation, you may already have pythontex on your system! Note that the pythontex package is not available on [Overleaf](https://overleaf.com).

### Typesetting

To typeset an assessment with pythontex you need to do the following steps:


   ::

      pdflatex -interaction=nonstopmode assessment.tex
      pythontex assessment.tex
      pdflatex -interaction=nonstopmode assessmnet.tex

There will be some files generated during each step, but the final pdf isn't produced until you run ``pdflatex`` the second time.

### Solutions

Solutions for the randomized problems are included in some (but not all!) of the assessments.  It's a work in progress.
 