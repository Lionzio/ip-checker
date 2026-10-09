# Gabarito SINTÉTICO (e2e): não é um gabarito oficial.
quantidade = int(input())
soma = 0
contador = 0
while contador < quantidade:
    valor = int(input())
    if valor % 2 == 0:
        soma = soma + valor
    contador = contador + 1
if soma > 100:
    print("muito", soma)
else:
    print("pouco", soma)
