from royalapp import new_window
from qtpy.QtWidgets import QTableWidget, QTableWidgetItem

def make_table(shape: tuple[int, int]):
    nr, nc = shape
    table = QTableWidget(nr, nc)
    for i in range(nr):
        for j in range(nc):
            table.setItem(i, j, QTableWidgetItem(f"Item {i} {j}"))
    return table

def main():
    ui = new_window()

    table1 = make_table((3, 3))
    table2 = make_table((4, 4))
    ui.add_widget(table1)
    ui.add_widget(table2)
    ui.show(run=True)

if __name__ == "__main__":
    main()
