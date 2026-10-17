# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L3-Q3, sem nenhum código de aluno. Revise antes do merge.
print("Sistema HeisenbergOS v2.0 - Monitor do Reator Inicializado...\n")

operador = input()
pressao_str = input()
status_mike = input()

if not pressao_str.isdigit():
    print("Yo Jesse! Você colocou tempero onde devia ter um número de pressão! O reator pifou!")
else:
    pressao_tanque = int(pressao_str)
    
    if operador == "Hank Schrader" or operador == "Gomez":
        print("Alerta Vermelho: Agente do DEA detectado no laboratório!")
        
    status_mike_sem_espacos = status_mike.replace(" ", "")
    if status_mike_sem_espacos.isupper():
        print("Abaixe o tom de voz! Mike está escutando no microfone!")
        
    status_mike_normalizado = status_mike.lower().strip()
    
    reagentes_base = ("Metilamina", "Fenilacetona", "Hidróxido de Sódio", "Ácido Clorídrico", "Metilamina")
    quantidades_ml = (500, 250, 150, 100, 300)
    
    ultimo_ingrediente = ""
    
    while True:
        acao_tupla = input()
        if acao_tupla == "FIM":
            break
            
        elif acao_tupla == "contar":
            ingrediente_alvo = input()
            ultimo_ingrediente = ingrediente_alvo
            contador = 0
            for r in reagentes_base:
                if r == ingrediente_alvo:
                    contador += 1
            if contador > 0:
                print(f"O ingrediente {ingrediente_alvo} aparece {contador} vez(es) na receita base.")
            else:
                print(f"O Ingrediente {ingrediente_alvo} não foi encontrado, precisamos melhorar o nosso estoque!")
                
        elif acao_tupla == "posicao":
            ingrediente_alvo = input()
            ultimo_ingrediente = ingrediente_alvo
            pos = -1
            for i in range(len(reagentes_base)):
                if reagentes_base[i] == ingrediente_alvo:
                    pos = i
                    break
            if pos != -1:
                print(f"O ingrediente {ingrediente_alvo} foi encontrado primeiro na posicao {pos} da tupla.")
            else:
                print(f"Ingrediente {ingrediente_alvo} nao encontrado no registro fixo!")
                
        elif acao_tupla == "varrer":
            ingrediente_alvo = input()
            ultimo_ingrediente = ingrediente_alvo
            soma_total = 0
            for i in range(len(reagentes_base)):
                if reagentes_base[i] == ingrediente_alvo:
                    ml = quantidades_ml[i]
                    soma_total += ml
                    print(f"Lote encontrado: {ingrediente_alvo} - {ml}ml")
            print(f"Volume total de {ingrediente_alvo} no reator: {soma_total}ml")
            
        elif acao_tupla == "concatenar":
            novo_elemento = input()
            nova_quantidade = int(input())
            reagentes_base = reagentes_base + (novo_elemento,)
            quantidades_ml = quantidades_ml + (nova_quantidade,)
            tamanho = len(reagentes_base)
            print(f"Ingrediente adicionado à nova tupla! Tamanho atualizado: {tamanho}")
            
        elif acao_tupla == "desempacotar":
            r1, m1 = reagentes_base[-3], quantidades_ml[-3]
            r2, m2 = reagentes_base[-2], quantidades_ml[-2]
            r3, m3 = reagentes_base[-1], quantidades_ml[-1]
            print(f"Últimos 3 reativos do registro: {r1} ({m1}ml), {r2} ({m2}ml) e {r3} ({m3}ml).")
            
    if pressao_tanque >= 50 and status_mike_normalizado == "tranquilo":
        print("Reação perfeita! Lote de 99.1% de pureza pronto para distribuição.")
    elif pressao_tanque < 15:
        print("Pressão crítica muito baixa! A mistura estragou, descarte o lote!")
    elif status_mike_normalizado == "alerta" and len(reagentes_base) > 5:
        print("A receita ficou muito complexa para o tempo hábil! Limpe o reator antes que Mike chegue!")
    else:
        print("Ajustando exaustores... Mantenha o reator sob observação!")
