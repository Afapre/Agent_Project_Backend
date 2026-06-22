import React from 'react';
import ChatWindow from '../../frontend/src/components/ChatWindow';
import './App.css';

/**
 * Root Application Element wrapper.
 * Acts as a clean structural viewport frame holding the isolated ChatWindow component.
 */
function App() {
  return (
    <div className="app-container">
      {/* Mount the HTML interface layout component module directly on screen */}
      <ChatWindow />
    </div>
  );
}

export default App;