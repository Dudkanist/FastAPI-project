def clean_sequence(seq: str) -> str:
    """
    Удаляет пробелы и переводит в верхний регистр
    """
    return seq.replace(" ", "").upper()

def calculate_gc_content(seq: str) -> float:
    """
    Расчет процента G и C в последовательности
    """
    
    if not seq:
        return 0.0
    
    seq = clean_sequence(seq)
    g_count = seq.count('G')
    c_count = seq.count('C')
    
    return round(((g_count + c_count) / len(seq)) * 100, 2)

def calculate_melting_temp(seq: str) -> float:
    """
    Расчет температуры плавления (Tm)
    Для коротких (< 14 bp): Tm = (A+T)*2 + (G+C)*4
    Для длинных: Tm = 64.9 + 41 * (G+C - 16.4) / (A+T+G+C)
    """
    seq = clean_sequence(seq)
    length = len(seq)
    
    if length == 0:
        return 0.0
        
    a_count = seq.count('A')
    t_count = seq.count('T')
    g_count = seq.count('G')
    c_count = seq.count('C')
    
    if length < 14:
        tm = (a_count + t_count) * 2 + (g_count + c_count) * 4
    else:
        tm = 64.9 + 41 * (g_count + c_count - 16.4) / length
        
    return round(tm, 2)

def calculate_molecular_weight(seq: str) -> float:
    """
    Упрощенный расчет молекулярной массы одноцепочечной ДНК (г/моль)
    A: 313.2, T: 304.2, G: 329.2, C: 289.2, фосфатный остов: 61.96
    """
    seq = clean_sequence(seq)
    weights = {'A': 313.2, 'T': 304.2, 'G': 329.2, 'C': 289.2}
    
    weight = sum(weights.get(base, 0) for base in seq)
    # Вычитаем воду, которая уходит при образовании фосфодиэфирной связи
    weight -= 61.96 * max(0, len(seq) - 1) 
    
    return round(weight, 2)
