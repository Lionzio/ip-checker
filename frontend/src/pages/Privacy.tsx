import { Link } from "react-router";

/**
 * Aviso de privacidade (S19-02; Q-16, Q-19 d, NFR-11). Descreve o que o sistema faz de fato; se os
 * dados guardados ou enviados a terceiros mudarem, este texto muda junto (DoD, seção 8).
 */
export function Privacy() {
  return (
    <article className="mx-auto flex max-w-3xl flex-col gap-4 py-6 leading-relaxed">
      <h2 className="text-2xl font-semibold">Aviso de privacidade</h2>
      <p>
        O IP-Checker é de uso exclusivo da equipe da disciplina de Introdução à Programação. Este aviso
        explica quais dados ele guarda, para quê, quem os vê e o que sai do servidor.
      </p>

      <h3 className="text-lg font-semibold">Dados da sua conta</h3>
      <ul className="list-disc pl-6">
        <li>
          Nome, e-mail institucional, curso e tratamento (masculino, feminino ou neutro), informados no
          registro e editáveis no perfil.
        </li>
        <li>
          A senha, guardada só como resumo criptográfico (Argon2id): ninguém, nem a equipe técnica,
          consegue lê-la. Quem entra pelo Google não tem senha guardada; fica só o identificador da
          conta Google.
        </li>
        <li>Cargo, situação da conta, data do pedido e quem o aprovou ou recusou.</li>
      </ul>
      <p>
        Esses dados servem para dar acesso só à equipe, aprovar os cadastros e montar a apresentação
        do feedback. Nome, e-mail, curso, cargo e situação aparecem na tela de gerenciamento, que só o
        desenvolvedor, os professores e os monitores-chefe acessam. O tratamento só você vê, e ele é
        usado apenas para escrever o feedback.
      </p>

      <h3 className="text-lg font-semibold">Código dos alunos</h3>
      <p>
        O código verificado, comparado no painel de plágio ou usado no feedback é analisado e
        descartado: não vai para o banco, para o disco nem para os logs, e nunca é executado.
      </p>

      <h3 className="text-lg font-semibold">Feedback</h3>
      <p>
        Quando há uma IA configurada, vão ao provedor dela só o código sem os comentários, a anotação
        e o resultado da verificação. O nome do aluno é trocado por [ALUNO] antes do envio, e o seu
        nome e o seu cargo não vão. Sem IA, o texto é montado por modelos no próprio servidor, e nada
        sai dele.
      </p>

      <h3 className="text-lg font-semibold">Sessão, e-mail e registros técnicos</h3>
      <ul className="list-disc pl-6">
        <li>
          A sessão fica num cookie que a página não consegue ler; o servidor guarda só o resumo do
          identificador. Ela termina depois de 12 horas sem uso, em no máximo 7 dias, ao sair, ao
          trocar a senha, ao mudar de cargo ou ao ser removido da equipe.
        </li>
        <li>O link de verificação do registro é enviado ao seu e-mail por um serviço de envio de e-mails.</li>
        <li>
          Os registros técnicos não guardam código, senhas, tokens nem o IP. O IP é usado só na memória
          do servidor, para o limite de requisições, e some em até 2 minutos.
        </li>
      </ul>

      <h3 className="text-lg font-semibold">Saída da equipe</h3>
      <p>
        Uma conta removida não é apagada: perde o acesso e guarda só o necessário ao histórico da
        equipe (nome, cargo e datas). Para corrigir os seus dados, use o perfil; para outros pedidos
        sobre eles, fale com o desenvolvedor da plataforma ou com a coordenação da disciplina.
      </p>

      <Link to="/" className="text-sm text-blue-700 underline dark:text-blue-300">
        Voltar ao início
      </Link>
    </article>
  );
}
