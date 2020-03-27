from PyQt5 import QtWidgets, uic, QtCore
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem
from pythonping import ping
from mainwindow import Ui_MainWindow
import sys, json, requests, os, shutil

class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super(Ui, self).__init__()
        # uic.loadUi('bipador.ui', self)
        # self.show()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        #Botões
        self.btConfirmar = self.findChild(QtWidgets.QPushButton, 'btConfirmar')
        self.btConfirmar.clicked.connect(self.confirmar)
        self.btConfirmar.setShortcut("Return")
        self.btEnviar = self.findChild(QtWidgets.QPushButton, 'btEnviar')
        self.btEnviar.clicked.connect(self.enviar)
        self.btCancelar = self.findChild(QtWidgets.QPushButton, 'btCancelar')
        self.btCancelar.clicked.connect(self.cancelar)

        #Caixas de texto
        self.tbPedido = self.findChild(QtWidgets.QLineEdit, 'tbPedido')
        self.tbIMEI = self.findChild(QtWidgets.QLineEdit, 'tbIMEI')
        self.tbIMEI.textEdited.connect(self.alteracaoIMEI)

        #Barra de Progresso
        self.pbProgresso = self.findChild(QtWidgets.QProgressBar, 'pbProgresso')

        #Abas
        self.tbAbas = self.findChild(QtWidgets.QTabWidget, 'tbAbas')

        #Lista
        self.lvIMEI = self.findChild(QtWidgets.QListWidget,'lvIMEI')
        self.lvIMEI.itemDoubleClicked.connect(lambda: self.apagarItem(self.lvIMEI.selectedItems()[0]))

        #Labels
        self.lbTotalCaixa = self.findChild(QtWidgets.QLabel,'lbTotalCaixa')
        self.lbTotalAparelho = self.findChild(QtWidgets.QLabel,'lbTotalAparelho')
        self.lbTotal = self.findChild(QtWidgets.QLabel,'lbTotal')

        #Tabelas
        self.tbDescricao = self.findChild(QtWidgets.QTableWidget,'tbDescricao')

        #Lista com os IMEIS (para evitar um grande processamento ao final)
        self.helper = []

    def confirmar(self):

        if self.testarConexao(): #Confirmar conexao
            self.validarPedido(self.tbPedido.text())

    def testarConexao(self):
        response = ping('10.66.96.2')
        if (response.rtt_avg_ms >= 2000): #Confirmar conexao
            self.alerta('Por favor, confira a sua conexão e tente novamente.')
            return 0
        return 1

    def validarPedido(self, pedido):
        if pedido == '': #Pedido Incorreto
            self.alerta('Pedido incorreto')
        else: #Pedido digitado
            url = "http://10.66.96.2:8090/rest/controleprodutos/itensnf"
            payload = "{\"notafiscal\":\"" + self.tbPedido.text().rjust(9,'0') + "\",\"serie\":\"1\"}"
            response = requests.request("POST", url, data=payload)
            pedido = response.text
            self.jPedido = json.loads(pedido)

            if self.jPedido["ITENS"][0]["CODIGOPRODUTO"].replace(' ','').isdigit(): #A nota existe
                self.montarPedido()
                self.btCancelar.setEnabled(True)
                self.btConfirmar.setEnabled(False)
                self.tbPedido.setEnabled(False)
                self.tbIMEI.setEnabled(True)
                self.tbAbas.setEnabled(True)
                self.lvIMEI.setEnabled(True)
                self.tbDescricao.setEnabled(True)
                self.tbAbas.setCurrentIndex(1)
            else: #A nota nao existe
                self.tbPedido.clear()
                self.alerta(self.jPedido["ITENS"][0]["CODIGOPRODUTO"])

    def montarPedido(self):
        self.total = 0
        for pedido in self.jPedido["ITENS"]:
            self.total = self.total + pedido["QTDITENS"]
        self.pbProgresso.setMaximum(self.total)

        self.tbDescricao.setRowCount(len(self.jPedido["ITENS"])+1)
        self.tbDescricao.setColumnCount(4)
        self.tbDescricao.setItem(0, 0, QTableWidgetItem('Item(s)'))
        self.tbDescricao.setItem(0, 1, QTableWidgetItem('Caixa(s)'))
        self.tbDescricao.setItem(0, 2, QTableWidgetItem('Aparelho(s)'))
        self.tbDescricao.setItem(0, 3, QTableWidgetItem('Total Bipado(s)'))

        lin = 1
        for i in self.jPedido["ITENS"]:
            self.tbDescricao.setItem(lin, 0, QTableWidgetItem(self.nome(i["CODIGOPRODUTO"].replace(' ',''))))
            self.tbDescricao.setItem(lin, 1, QTableWidgetItem(str(int(int(i["QTDITENS"])/20))))
            self.tbDescricao.setItem(lin, 2, QTableWidgetItem(str(int(i["QTDITENS"])%20)))
            self.tbDescricao.setItem(lin, 3, QTableWidgetItem('0'))
            lin = lin + 1

        header = self.tbDescricao.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.tbDescricao.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)

    def alerta(self, message, cancelar = 0):
        msgBox = QtWidgets.QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(message)
        msgBox.setWindowTitle("Aviso")
        if cancelar:
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.Cancel)
            buttonY = msgBox.button(QMessageBox.Yes)
            buttonY.setText("Sim")
            buttonC = msgBox.button(QMessageBox.Cancel)
            buttonC.setText("Cancelar")
        else:
            msgBox.setStandardButtons(QMessageBox.Ok)
        self.returnValue = msgBox.exec()

    def enviar(self):
        if self.testarConexao():
            url = "http://10.66.96.2:8090/rest/controleprodutos/validanumidentificador"
            payload = '{\"NotaFiscal\":\"' + self.tbPedido.text().rjust(9,'0') + '\",\r\n\"Serie\":\"1\",\r\n\"ListaNumIdentificador\":['
            for imei in self.helper:
                payload = payload + '\"' + imei + '\",'
            payload = payload[:len(payload) - 1] #remover ultima virgula
            payload = payload + ']}'
            response = requests.request("POST", url, data=payload)
            jResposta = json.loads(response.text)
            mensagem = ""
            if jResposta.get("LISTANUMIDENTIFICADORERRO"):
                self.alerta('Existe(m) IMEI(s) com problemas, por favor, apague(os) dos itens bipados.')
                for i in jResposta["LISTANUMIDENTIFICADORERRO"]:
                    mensagem = mensagem + i["DESCRICAOERRO"] + '\n'
                    self.apagarItem(self.lvIMEI.findItems(i["NUMIDENTIFICADOR"],QtCore.Qt.MatchExactly)[0])
                    # self.lvIMEI.takeItem(self.lvIMEI.row(self.lvIMEI.findItems(i["NUMIDENTIFICADOR"],QtCore.Qt.MatchExactly)[0]))
                mensagem = mensagem + '\n Atenção: Esse(s) produto(s) foi(rão) deletado(s) dos itens bipados'
                self.alerta(mensagem)
            else:
                self.alerta("Enviado com sucesso!")
                self.persistir()
                self.limpar()

    def cancelar(self):
        self.limpar()

    def alteracaoIMEI(self):
        if (len(self.tbIMEI.text())) > 1: #Evitar problema ao checar caixa, quando o usuário apagar todos os valores da caixa de texto.
            if self.tbIMEI.text().isdigit() and len(self.tbIMEI.text())>=15:
                self.enviarItem()
            elif self.tbIMEI.text()[0] == 'S' and len(self.tbIMEI.text())>=12:
                self.enviarItem()
            elif self.tbIMEI.text()[0] == 'M' and len(self.tbIMEI.text())>=14:
                self.enviarItem()

    def enviarItem(self):
        self.tbAbas.setCurrentIndex(0)
        if self.tbIMEI.text() in self.helper: #Testa se nao teve antes
            self.alerta('O item ' + self.tbIMEI.text() + ' já foi adicionado anteriormente')
            self.tbIMEI.clear()
        else:
            self.checarIMEI(self.tbIMEI.text())
            if self.totalAdicionar + self.qtdAtual > self.totalPedido:
                self.alerta('O item ' + self.tbIMEI.text() + ' não pode ser adicionado, pois ultrapassará a quantidade de aparelhos do pedido')
                self.tbIMEI.clear()
            elif self.totalAdicionar > 0:
                self.atualizarQuantidade('add', self.tbIMEI.text())
                self.lvIMEI.addItem(self.tbIMEI.text())
                self.helper.append(self.tbIMEI.text())
                self.tbIMEI.clear()
                self.lvIMEI.scrollToBottom()

    def apagarItem(self, item):
        self.alerta("Você realmente deseja apagar o item " + item.text() + " ?", 1)
        if self.returnValue == 16384: #16384 é o codigo para confirmacao de apagar
            self.atualizarQuantidade('remove',item.text())
            self.helper.remove(item.text())
            self.lvIMEI.takeItem(self.lvIMEI.row(item))

    def atualizarQuantidade(self,op,IMEI):
        if op == 'add':
            # if self.tbIMEI.text().isdigit():
            if IMEI.isdigit():
                self.lbTotalAparelho.setText(str(int(self.lbTotalAparelho.text())+1))
                self.lbTotal.setText(str(int(self.lbTotal.text())+1))
                self.tbDescricao.setItem(self.linha, 3, QTableWidgetItem(str(self.qtdAtual + 1))) #atualiza quantidade
            else:
                self.lbTotalCaixa.setText(str(int(self.lbTotalCaixa.text())+1))
                self.lbTotal.setText(str(int(self.lbTotal.text())+20))
                self.tbDescricao.setItem(self.linha, 3, QTableWidgetItem(str(self.qtdAtual + 20))) #atualiza quantidade


        elif op == 'remove':
            self.checarIMEI(IMEI)
            if IMEI[0].isdigit():
                self.lbTotalAparelho.setText(str(int(self.lbTotalAparelho.text())-1))
                self.lbTotal.setText(str(int(self.lbTotal.text())-1))
                self.tbDescricao.setItem(self.linha, 3, QTableWidgetItem(str(self.qtdAtual - 1))) #atualiza quantidade

            else:
                self.lbTotalCaixa.setText(str(int(self.lbTotalCaixa.text())-1))
                self.lbTotal.setText(str(int(self.lbTotal.text())-20))
                self.tbDescricao.setItem(self.linha, 3, QTableWidgetItem(str(self.qtdAtual - 20))) #atualiza quantidade


        self.pbProgresso.setValue(int(self.lbTotal.text()))
        if self.pbProgresso.value() == self.pbProgresso.maximum():
            self.tbIMEI.setEnabled(False)
            self.btEnviar.setEnabled(True)
        else:
            self.tbIMEI.setEnabled(True)
            self.btEnviar.setEnabled(False)

    def checarIMEI(self, IMEI):
        if self.testarConexao():
            url = "http://10.66.96.2:8090/rest/controleprodutos/modeloaparelho"
            payload = "{\"NumIdentificador\":\""+IMEI+"\"}"
            response = requests.request("POST", url, data = payload)
            jModelo = json.loads(response.text) #Pega o modelo com o IMEI
            self.totalPedido, self.qtdAtual, self.totalAdicionar = 0, 0, 0
            if (jModelo['CODIGO']): #Testa se o IMEI existe
                for i in range(len(self.jPedido["ITENS"])):
                    if self.tbDescricao.item(i+1,0).text() == self.nome(jModelo['CODIGO']): #Achou o aparelho no pedido
                        self.totalPedido = int(self.tbDescricao.item(i+1,2).text()) + 20*int(self.tbDescricao.item(i+1,1).text())
                        self.qtdAtual = int(self.tbDescricao.item(i+1,3).text())
                        self.totalAdicionar = 1 if self.tbIMEI.text().isdigit() else 20
                        self.linha = i + 1
                        break
                if (self.totalAdicionar == 0):
                    self.alerta('O IMEI ' + self.tbIMEI.text() + ' não faz parte do pedido')
                    self.tbIMEI.clear()
            else:
                self.alerta('O IMEI ' + self.tbIMEI.text() + ' não é válido')
                self.tbIMEI.clear()

    def limpar(self):
        self.btCancelar.setEnabled(False)
        self.btEnviar.setEnabled(False)
        self.btConfirmar.setEnabled(True)
        self.tbPedido.setEnabled(True)
        self.tbPedido.clear()
        self.tbIMEI.setEnabled(False)
        self.tbIMEI.clear()
        self.tbAbas.setEnabled(False)
        self.lvIMEI.clear()
        self.lbTotalAparelho.setText('0')
        self.lbTotalCaixa.setText('0')
        self.lbTotal.setText('0')
        self.pbProgresso.setValue(0)
        self.tbAbas.setCurrentIndex(0)
        self.tbDescricao.clear()
        self.helper.clear()

    def nome(self,cod):
        if cod == '000002': return 'CEL. RED MOBILE MEGA M010F - PRETO/VERMELHO'
        if cod == '000003': return 'CEL. RED MOBILE MEGA M010F - PRETO/AZUL'
        if cod == '000004': return 'CEL. RED MOBILE MEGA M010F - PRETO/AMARELO'
        if cod == '000005': return 'CEL. RED MOBILE PRIME 2.4 M012F - DOURADO'
        if cod == '000006': return 'CEL. RED MOBILE PRIME 2.4 M012F - PRETO'
        if cod == '000007': return 'CEL. RED MOBILE PRIME 2.4 M012F - PRATA'
        if cod == '000008': return 'CEL. RED MOBILE FIT MUSIC M011F - PRETO/VERMELHO'
        if cod == '000009': return 'CEL. RED MOBILE FIT MUSIC M011F - PRETO/LARANJA'
        if cod == '000010': return 'CEL. RED MOBILE FIT MUSIC M011F - PRETO/AMARELO'
        if cod == '000011': return 'CEL. RED MOBILE FIT MUSIC M011F - PRETO/AZUL'
        if cod == '000012': return 'SMARTPHONE RED MOBILE QUICK 5.0 S50 - VERMELHO E PRATA'
        return (cod + ' Codigo nao encontrado')

    def persistir(self):
        imei = open(self.tbPedido.text() + " - IMEIs" + ".txt","w+")
        cm = open(self.tbPedido.text() + " - CMs" + ".txt","w+")
        for i in self.helper:
            if i.isdigit():
                imei.write(i + "\n")
            else:
                cm.write(i + "\n")
        imei.write("Chave: " + str(int(self.tbPedido.text())*24 + 23))
        cm.write("Chave: " + str(int(self.tbPedido.text())*23 + 24))
        imei.close()
        cm.close()

        dir = "C:\\Bipador\\Backup\\"
        try:
            os.makedirs(dir)
        except:
            pass

        shutil.copy2(self.tbPedido.text() + " - IMEIs" + ".txt", dir)
        shutil.copy2(self.tbPedido.text() + " - IMEIs" + ".txt", dir)

app = QtWidgets.QApplication(sys.argv)
application = Ui()
application.show()
sys.exit(app.exec_())
# window = Ui()
# app.exec_()
# exit ()
