"""Keep modal scrolling inside its window, before ttk class and global bindings."""
import math


def bind_modal_wheel(window, fallback=None):
    tag = 'BbModalWheel' + str(window)
    remainder = {}

    def wheel(event):
        widget = event.widget
        if widget is window:
            widget = window.winfo_containing(event.x_root, event.y_root) or window
        target = None
        while widget is not None and widget is not window:
            if widget.winfo_class() in ('Treeview', 'Text', 'Canvas', 'Listbox'):
                target = widget
                break
            widget = getattr(widget, 'master', None)
        target = target or fallback
        if target is not None:
            horizontal = bool(event.state & 1)
            key = (str(target), horizontal)
            delta = -1 if getattr(event, 'num', None) == 4 else 1 if getattr(event, 'num', None) == 5 else -event.delta/120
            total = remainder.get(key, 0) + delta*3
            steps = math.trunc(total)
            remainder[key] = total-steps
            if steps:
                (target.xview_scroll if horizontal else target.yview_scroll)(steps, 'units')
        return 'break'

    sequences = ('<MouseWheel>', '<Shift-MouseWheel>', '<Button-4>', '<Button-5>')
    for sequence in sequences:
        window.bind_class(tag, sequence, wheel)

    def attach(widget):
        widget.bindtags((tag, *widget.bindtags()))
        for child in widget.winfo_children():
            attach(child)
    attach(window)

    def cleanup(event):
        if event.widget is window:
            for sequence in sequences:
                window.unbind_class(tag, sequence)
    window.bind('<Destroy>', cleanup, add='+')
