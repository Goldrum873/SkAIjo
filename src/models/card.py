class Card:
    def __init__(self, value: int):
        self.value = value
        self.visible = False
    
    def __str__(self):
        return str(self.value) if self.visible else "X"
    
    def __repr__(self):
        return f"Card({self.value}, {'visible' if self.visible else 'hidden'})"