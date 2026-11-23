import React from 'react'
import Header from '../components/Header'
import Body from '../components/Body'
import Footer from '../components/Footer'

const Chat = () => {
  return (
    <div className="relative h-dvh flex flex-col overflow-hidden">
      <Header />

      <main className="relative flex-1 min-h-0">
        <Body />
      </main>

      <Footer />
    </div>
  )
}

export default Chat