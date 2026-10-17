# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L3-Q3, sem nenhum código de aluno. Revise antes do merge.
def main():
    print("Sistema HeisenbergOS v2.0 - Monitor do Reator Inicializado...\n")
    
    operador = input()
    pressao_str = input()
    status_mike = input()
    
    if not pressao_str.lstrip('-').replace('.', '', 1).isdigit():
        print("Yo Jesse! Você colocou tempero onde devia ter um número de pressão! O reator pifou!")
        return
        
    pressao_tanque = float(pressao_str)
    
    if operador in ("Hank Schrader", "Gomez"):
        print("Alerta Vermelho: Agente do DEA detectado no laboratório!")
        
    status_mike_limpo = "".join(status_mike.split()).lower()
    if status_mike != status_mike_limpo or any(c.isupper() for c in status_mike if c.isalpha()):
        if any(c.isupper() for c in status_mike if c.isalpha()) or status_mike != status_mike_limpo:
            pass
    # O enunciado diz: "Se o status_mike estiver inteiramente em maiúsculas (Considere que a entrada pode conter espaços entre as letras e variações de maiúsculo e minúsculo , ex: "A Le rT A, "tra nqu ilo"" )" -> Na verdade, checa se tem alguma letra maiúscula ou se difere da versão sem espaços/minúscula. Pela lógica do Exemplo 3 ("TRANQUILO"), vamos verificar se há letras maiúsculas ou espaços.
    status_sem_espacos = status_mike.replace(" ", "")
    if status_sem_espacos and status_sem_espacos.isupper():
        print("Abaixe o tom de voz! Mike está escutando no microfone!")
        
    reagentes_base = ("Metilamina", "Fenilacetona", "Hidróxido de Sódio", "Ácido Clorídrico", "Metilamina")
    quantidades_ml = (500, 250, 150, 100, 300)
    
    ultimo_ingrediente = ""
    
    while True:
        acao = input()
        if acao == "FIM":
            break
            
        if acao == "contar":
            ingrediente = input()
            ultimo_ingrediente = ingrediente
            contador = 0
            for r in reagentes_base:
                if r == ingrediente:
                    contador += 1
            if contador > 0:
                print(f"O ingrediente {ingrediente} aparece {contador} vez(es) na receita base.")
            else:
                print(f"O Ingrediente {ingrediente} não foi encontrado, precisamos melhorar o nosso estoque!")
                
        elif acao == "posicao":
            ingrediente = input()
            ultimo_ingrediente = ingrediente
            pos = -1
            for i in range(len(reagentes_base)):
                if reagentes_base[i] == ingrediente:
                    pos = i
                    break
            if pos != -1:
                print(f"O ingrediente {ingrediente} foi encontrado primeiro na posicao {pos} da tupla.")
            else:
                print(f"Ingrediente {ingrediente} nao encontrado no registro fixo!")
                
        elif acao == "varrer":
            ingrediente = input()
            ultimo_ingrediente = ingrediente
            soma_total = 0
            for i in range(len(reagentes_base)):
                if reagentes_base[i] == ingrediente:
                    ml = quantidades_ml[i]
                    print(f"Lote encontrado: {ingrediente} - {ml}ml")
                    soma_total += ml
            print(f"Volume total de {ingrediente} no reator: {soma_total}ml")
            
        elif acao == "concatenar":
            novo_elemento = input()
            nova_quantidade = int(input())
            ultimo_ingrediente = novo_elemento
            reagentes_base = reagentes_base + (novo_elemento,)
            quantidades_ml = quantidades_ml + (nova_quantidade,)
            print(f"Ingrediente adicionado à nova tupla! Tamanho atualizado: {len(reagentes_base)}")
            
        elif acao == "desempacotar":
            r1, m1 = reagentes_base[-3], quantidades_ml[-3]
            r2, m2 = reagentes_base[-2], quantidades_ml[-2]
            r3, m3 = reagentes_base[-1], quantidades_ml[-1]
            print(f"Últimos 3 reativos do registro: {r1} ({m1}ml), {r2} ({m2}ml) e {r3} ({m3}ml).")

    # Fase 4
    status_mike_normalizado = status_mike.replace(" ", "").lower()
    tamanho_tupla = len(reagentes_base)
    
    if pressao_tanque >= 50 and status_mike_normalizado == "tranquilo":
        print("Reação perfeita! Lote de 99.1% de pureza pronto para distribuição.")
    elif pressao_tanque < 15:
        print("Pressão crítica muito baixa! A mistura estragou, descarte o lote!")
    elif status_mike_normalizado == "alerta" and tamanho_tupla > 5:
        print("A receita ficou muito complexa para o tempo hábil! Limpe o reator antes que Mike chegue!")
    else:
        print("Ajustando exaustores... Mantenha o reator sob observação!")

if __name__ == "__main__":
    main()
