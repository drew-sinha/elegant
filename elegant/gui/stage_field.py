# This code is licensed under the MIT License (see LICENSE file for details)

import itertools
from PyQt5 import Qt
from ris_widget.qwidgets import annotator

class StageField(annotator.AnnotationField):
    FIRST_COLOR = (255, 255, 255)
    LAST_COLOR = (184, 184, 184)
    COLOR_CYCLE = itertools.cycle([(184, 255, 184), (255, 255, 184), (184, 184, 255), (255, 184, 184), (255, 184, 255)])

    def __init__(self, name='stage', stages=['egg', 'larva', 'adult', 'dead'], transitions=['hatch', 'adult', 'dead'], shortcuts=None):
        """Annotate the life-stage of a worm.

        Parameters:
            name: annotation name
            stages: list of life stages to annotate, generally starting with egg
                and ending with dead.
            transitions: names of the transitions between life stages.
            shortcuts: shortcut keys to select the different transitions; if not
                specified, the first letter of each transition will be used.
        """
        assert len(transitions) == len(stages) - 1
        self.stages = stages
        self.stage_indices = {stage:i for i, stage in enumerate(stages)}
        self.transitions = transitions
        if shortcuts is None:
            # take the first letter of each as the shortcut
            shortcuts = [transition[0] for transition in transitions]
        self.shortcuts = shortcuts
        self.colors = {stages[0]: self.FIRST_COLOR, stages[-1]: self.LAST_COLOR}
        self.colors.update(zip(stages[1:-1], self.COLOR_CYCLE))
        super().__init__(name)

    def init_widget(self):
        self.widget = Qt.QGroupBox(self.name)
        layout = Qt.QHBoxLayout()
        self.widget.setLayout(layout)
        self.label = Qt.QLabel()
        layout.addWidget(self.label)
        for transition, key, next_stage in zip(self.transitions, self.shortcuts, self.stages[1:]):
            button = Qt.QPushButton(transition)
            callback = self._make_transition_callback(next_stage)
            button.clicked.connect(callback)
            layout.addWidget(button)
            Qt.QShortcut(key, self.widget, callback, context=Qt.Qt.ApplicationShortcut)

    def _make_transition_callback(self, next_stage):
        def callback():
            self.set_stage(next_stage)
        return callback

    def set_stage(self, stage):
        self.update_annotation(stage)
        # now fix up pages before this page to comply with newly set stage
        fb_i = self.flipbook.pages.index(self.page)
        youngest_stage_i = self.stage_indices[stage] - 1
        # we can never manually set the first stage, so youngest_stage_i is always >= 0
        if fb_i > 0:    # Exclude update of previous pages if this is the first image
            for page in self.flipbook.pages[fb_i-1::-1]:
                page_stage = self.get_annotation(page)
                page_stage_i = self.stage_indices.get(page_stage, len(self.stages)) # will be > all others if stage is None
                if page_stage_i < youngest_stage_i:
                    youngest_stage_i = page_stage_i
                else:
                    page.annotations[self.name] = self.stages[youngest_stage_i]

        # pages after this will be brought into compliance by update_widget
        self.update_widget(stage)

    def update_widget(self, value):
        if value is None:
            self.label.setText('')
        elif value not in self.stages:
            raise ValueError('Value {} not in list of stages.'.format(value))
        else:
            self.label.setText(value)

        # now ensure that all pages follow correct stage ordering, and set
        # the page colors
        oldest_stage_i = -1
        for page in self.flipbook.pages:
            page_stage = self.get_annotation(page)
            page_stage_i = self.stage_indices.get(page_stage, -1) # will be < all others if stage is None
            if page_stage_i > oldest_stage_i:
                oldest_stage_i = page_stage_i
            elif page_stage_i < oldest_stage_i:
                # NB: if both are -1, then we haven't actually seen any annotations yet,
                # so we shouldn't do anything. Hence the test above for strict inequality.
                page_stage = page.annotations[self.name] = self.stages[oldest_stage_i]

            if page_stage is None:
                page.color = None
            else:
                page.color = self.colors[page_stage]
