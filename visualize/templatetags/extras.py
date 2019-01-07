from django import template

register = template.Library()


@register.filter(name='inter')
def inter(word):
    dictionary = {
        'antenna': 'Линейная антенная решетка',
        'controlled_connections': 'АФАР с управляемыми связями',
        'adaptive_filtering': 'Антенна с адаптивной пространственной фильтрацией',
        'fi_interference': 'Направление прихода помех'
    }
    return dictionary.get(word, word)