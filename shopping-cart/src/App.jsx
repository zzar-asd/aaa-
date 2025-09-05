import { useState } from 'react'
import './App.css'

function App() {
  // 购物车状态
  const [cart, setCart] = useState([]);

  // 商品列表数据
  const products = [
    { id: 1, name: '商品A', price: 100 },
    { id: 2, name: '商品B', price: 200 },
    { id: 3, name: '商品C', price: 300 },
  ];

  // 添加商品到购物车
  const addToCart = (product) => {
    setCart(prevCart => {
      const existingItem = prevCart.find(item => item.id === product.id);
      if (existingItem) {
        return prevCart.map(item =>
          item.id === product.id ? { ...item, quantity: item.quantity + 1 } : item
        );
      } else {
        return [...prevCart, { ...product, quantity: 1 }];
      }
    });
  };

  // 从购物车移除商品
  const removeFromCart = (productId) => {
    setCart(prevCart => prevCart.filter(item => item.id !== productId));
  };

  return (
    <>
      <h1>电商购物车示例</h1>
      
      <div className="products">
        <h2>商品列表</h2>
        {products.map(product => (
          <div key={product.id} className="product">
            <span>{product.name} - ¥{product.price}</span>
            <button onClick={() => addToCart(product)}>加入购物车</button>
          </div>
        ))}
      </div>

      <div className="cart">
        <h2>购物车</h2>
        {cart.length === 0 ? (
          <p>购物车为空</p>
        ) : (
          <ul>
            {cart.map(item => (
              <li key={item.id}>
                {item.name} x {item.quantity} - ¥{item.price * item.quantity}
                <button onClick={() => removeFromCart(item.id)}>移除</button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </>
  )
}

export default App
