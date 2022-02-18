from flask import Flask
from flask import request as rq

import requests
app = Flask(__name__)
@app.route('/orders-create',methods=['POST'])
def crearOrden():
    serverMonolito='http://34.71.169.79/'
    serverMicroservicios='http://34.111.50.218/'
    token = rq.headers.get('Authorization').split(' ')[1]
    userid = rq.json["user_id"]
    productid = rq.json["product_id"]

    ######################VALIDACIONES Y CONSULTAS##################################################
    #Validacion de sesion
    response = requests.get(serverMonolito+'sesion/'+token)



    if(response.json().get('message')=='La sesión no existe' or response.status_code == 404):
        return {"message": "Sesion invalida"}, 404
    else:
        if(response.json().get("user_id")!=userid):
            return {"message": "Sesion invalida"}, 404

    #validar existencia del producto
    response = requests.get(serverMonolito+'producto/' + productid)

    if (response.json().get('message') == 'El producto no existe' or response.status_code == 404):
        return {"message": "El producto no existe"}, 404
    else:
        if (response.json().get("id") != productid):
            return {"message": "El producto no existe"}, 404


    #obtener id proveedor
    response = requests.get(serverMicroservicios+'sellers/item/' + productid)
    sellerid = response.json().get('uuid')
    if (sellerid == '' or response.status_code == 404 or sellerid == None):
        return {"message": "El producto no tiene un proveedor asociado"}, 404

    ######################HASTA ESTE PUNTO NO SE REQUIERE REVERSAR NADA##################################################

    #crear orden
    myobj = {"item": {"uuid":productid},"seller": {"uuid": sellerid},"user": {"uuid": userid}}

    response = requests.post(serverMicroservicios+'orders', json=myobj)
    orderid = response.json().get('orderId')
    if (response.json().get('orderId') == '' or response.status_code == 404 or response.json().get('orderId') == None):
        return {"message": "Ocurrio un error al intentar craer la orden, intenlo mas tarde"}, 404

    print(orderid+"order id")
    #crear agendamiento
    myobj = {"uuid": orderid}
    response = requests.post(serverMicroservicios+'agenda/sellers/'+sellerid, json=myobj)
    msgAgenda = response.json().get('msg')
    if (response.status_code != 201):
        ##Reversar order
        reverse = requests.delete(serverMicroservicios+'orders/'+orderid)
        return {"message": "Pedido rechazado, "+msgAgenda}, 404

    #realizar solicitud de pago
    myobj ={"order": {"uuid":orderid},"user": {"uuid": userid}}
    response = requests.post(serverMicroservicios + 'payments' , json=myobj)

    if (response.status_code == 412):
        message = ""
        if (response.json().get('msg') == None):
            message = "ya existe un pago activo asociado al pedido"
        else:
            message = response.json().get('msg')
        ##Reversar agenda
        reverse = requests.delete(serverMicroservicios + 'agenda/sellers/'+sellerid+'/order/'+ orderid)
        ##Reversar orden
        reverse = requests.delete(serverMicroservicios+'orders/'+orderid)

        return {"message": "Pedido rechazado, "+message}, 404

    else:
        if (response.status_code != 201):
            return {"message": "Pedido rechazado, disculpe las molestias"}, 404


    return  {"message": "Orden creada con exito y proceso de pago exitoso"}, 202