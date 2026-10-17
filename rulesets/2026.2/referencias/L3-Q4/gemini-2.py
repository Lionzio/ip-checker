# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L3-Q4, sem nenhum código de aluno. Revise antes do merge.
def calcular_mediana(lista):
    l = sorted(lista)
    n = len(l)
    if n % 2 == 1:
        return l[n // 2]
    else:
        return round((l[n // 2 - 1] + l[n // 2]) / 2, 1)

print("Espaço: a fronteira final. Estas são as viagens da nave estelar Enterprise…")
print("Sua missão de cinco anos: explorar novos mundos, procurar novas vidas e novas civilizações, audaciosamente indo aonde nenhum homem jamais esteve.")
print("Dr. McCoy: Eu sou um médico, não um matemático. Mas tenho que fazer o que precisa ser feito.")
print("=====")

tamanho_amostra = int(input())

while tamanho_amostra < 5 or tamanho_amostra > 12:
    print("Dr. McCoy: Esse número não é ideal, é possível trazer uma amostra de 5 a 12 indivíduos?")
    tamanho_amostra = int(input())

print(f"Dr. McCoy: Certo, {tamanho_amostra} indivíduos. É um número bom.")
print("=====")

temperaturas = []
pulsos = []
gases = []
pressoes = []

for _ in range(tamanho_amostra):
    linha = input()
    partes = linha.split(" - ")
    temp = float(partes[0].replace(" °C", ""))
    pulso = float(partes[1].replace(" bpm", ""))
    gas = float(partes[2].replace(" irpm", ""))
    pressao = float(partes[3].replace(" mmHg", ""))
    
    temperaturas.append(temp)
    pulsos.append(pulso)
    gases.append(gas)
    pressoes.append(pressao)

temperaturas.sort()
pulsos.sort()
gases.sort()
pressoes.sort()

temp_mediana = calcular_mediana(temperaturas)
pulso_mediana = calcular_mediana(pulsos)
gas_mediana = calcular_mediana(gases)
pressao_mediana = calcular_mediana(pressoes)

print("Relatório de dados da amostra:")
print(f"Temperatura: {temperaturas}")
print(f"Mediana: {temp_mediana}")
print(f"Frequência de pulso fluido: {pulsos}")
print(f"Mediana: {pulso_mediana}")
print(f"Frequência de troca gasosa: {gases}")
print(f"Mediana: {gas_mediana}")
print(f"Pressão interna de homeostase: {pressoes}")
print(f"Mediana: {pressao_mediana}")
print("=====")

print("Dr. McCoy: Agora irei medir os sinais do paciente.")
print("=====")

linha_paciente = input()
partes_p = linha_paciente.split(" - ")
temp_p = float(partes_p[0].replace(" °C", ""))
pulso_p = float(partes_p[1].replace(" bpm", ""))
gas_p = float(partes_p[2].replace(" irpm", ""))
pressao_p = float(partes_p[3].replace(" mmHg", ""))

temp_diff = round(temp_p - temp_mediana, 1)
pulso_diff = round(pulso_p - pulso_mediana, 1)
gas_diff = round(gas_p - gas_mediana, 1)
pressao_diff = round(pressao_p - pressao_mediana, 1)

sinais_criticos = 0
if temp_p < temperaturas[0] or temp_p > temperaturas[-1]:
    sinais_criticos += 1
if pulso_p < pulsos[0] or pulso_p > pulsos[-1]:
    sinais_criticos += 1
if gas_p < gases[0] or gas_p > gases[-1]:
    sinais_criticos += 1
if pressao_p < pressoes[0] or pressao_p > pressoes[-1]:
    sinais_criticos += 1

if sinais_criticos >= 2:
    avaliacao = "Alerta Crítico"
else:
    avaliacao = "Estável"

print("Relatório final:")
print(f"Temperatura do paciente: {temp_p}")
print(f"Diferença para a mediana: {temp_diff}")
print(f"Frequência de pulso fluido do paciente: {pulso_p}")
print(f"Diferença para a mediana: {pulso_diff}")
print(f"Frequência de troca gasosa: {gas_p}")
print(f"Diferença para a mediana: {gas_diff}")
print(f"Pressão interna de homeostase: {pressao_p}")
print(f"Diferença para a mediana: {pressao_diff}")
print(f"Quantidade de sinais críticos encontrados: {sinais_criticos}")
print(f"Avaliação final: {avaliacao}")
print("=====")
print("Dr. McCoy: Certo, agora sei o que fazer.")
