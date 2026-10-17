# Solução gerada por IA (S42-04, ADR-08): gemini, modelo gemini-3.5-flash-lite, 17/10/2026.
# Só a partir do enunciado da L2-Q5, sem nenhum código de aluno. Revise antes do merge.
def main():
    print("Quando percebi que contara oito mortes, senti o peso da minha própria lenda")
    
    qnt_ataques = int(input())
    
    if qnt_ataques == 0:
        print("Até logo, velho amigo... É bom saber que finalmente posso respirar fundo e apenas viver o dia de hoje.")
        return
    
    desfecho_alcancado = False
    
    for _ in range(qnt_ataques):
        print("Preciso encontrar esse mapa a qualquer custo, nem que seja a última coisa que eu faça com esta vida!")
        
        companheiro = input()
        
        if companheiro == "cao perrito":
            print("Olha só... de todas as criaturas do mundo, justo você tinha que decidir me seguir com esse rabo abanando?")
            N = int(input())
            todos_divisiveis_por_3 = True
            for _ in range(N):
                num = int(input())
                if num % 3 != 0:
                    todos_divisiveis_por_3 = False
            
            if todos_divisiveis_por_3:
                print("Bom trabalho, meu garoto! Quem diria que um cãozinho tão pequeno seria o grande herói do dia?")
                desfecho_alcancado = True
                break
                
        elif companheiro == "kitty patamansa":
            print("Kitty... Olhar para você de novo só me faz lembrar que, entre todas as minhas nove vidas, o meu maior erro foi ter deixado você esperando.")
            item = input()
            if item == "chapeu do gato" or item == "bota do gato":
                print("Impressionante, Kitty... Sempre soube que você era rápida, mas admito que nada fica melhor nas mãos da melhor ladra de Tão Tão Distante do que um presente para mim.")
                desfecho_alcancado = True
                break
        else:
            while True:
                frase = input()
                tem_desfecho = "Desfecho" in frase
                tem_morte = "Morte" in frase
                
                if tem_desfecho:
                    desfecho_alcancado = True
                    break
                elif tem_morte:
                    break
            if desfecho_alcancado:
                break

    if desfecho_alcancado:
        print("Parece que essa família de ursos e sua cachinhos acabam de provar do verdadeiro felino de botas!")
        frase_gato = input()
        if "coragem" in frase_gato.lower():
            print("A verdadeira vitória não está em vencer a morte, mas em encará-la de frente e escolher lutar por cada segundo desta vida!")
        else:
            print("Pode levar minha espada e meu chapéu... Eu lutei até o fim, mas hoje a lenda finalmente descansa.")
    else:
        print("Pode levar minha espada e meu chapéu... Eu lutei até o fim, mas hoje a lenda finalmente descansa.")

if __name__ == "__main__":
    main()
