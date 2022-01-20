/*==============================================================================

  Copyright (c) Kitware, Inc.

  See http://www.slicer.org/copyright/copyright.txt for details.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

  This file was originally developed by Julien Finet, Kitware, Inc.
  and was partially funded by NIH grant 3P41RR013218-12S1

==============================================================================*/

#ifndef __qLungAIRAppMainWindow_h
#define __qLungAIRAppMainWindow_h

// LungAIR includes
#include "qLungAIRAppExport.h"
class qLungAIRAppMainWindowPrivate;

// Slicer includes
#include "qSlicerMainWindow.h"

class Q_LUNGAIR_APP_EXPORT qLungAIRAppMainWindow : public qSlicerMainWindow
{
  Q_OBJECT
public:
  typedef qSlicerMainWindow Superclass;

  qLungAIRAppMainWindow(QWidget *parent=0);
  virtual ~qLungAIRAppMainWindow();

public slots:
  void on_HelpAboutLungAIRAppAction_triggered();

protected:
  qLungAIRAppMainWindow(qLungAIRAppMainWindowPrivate* pimpl, QWidget* parent);

private:
  Q_DECLARE_PRIVATE(qLungAIRAppMainWindow);
  Q_DISABLE_COPY(qLungAIRAppMainWindow);
};

#endif
