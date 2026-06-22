import { useState, useRef, useEffect } from 'react';

// Dynamically reads the endpoint value from environment variables file
const CHAT_ENDPOINT = process.env.REACT_APP_CHAT_ENDPOINT;

/**
 * Custom React Hook to manage CLARA chat state, memory, and API pipelines.
 * Includes explicit loading states to prevent input spam during generation phases.
 */
export function useClaraChat() {
  // Array state storing all active user, assistant, and error message objects
  const [messages, setMessages] = useState([]);
  
  // String state storing text currently typed inside the text input box
  const [input, setInput] = useState("");
  
  // Boolean state tracking whether the AI agent is actively processing a request
  const [isLoading, setIsLoading] = useState(false);
  
  // React Reference pointing directly to the chat window DOM node for scroll management
  const chatBoxRef = useRef(null);



  /**
   * Side Effect Hook: Automatically triggers every time the messages array updates.
   * Forces the chat display panel to smoothly scroll down to display the latest message.
   */
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [messages]);



  /**
   * Main function to package conversation history and dispatch payloads to the backend API.
   */
  const handleSend = async () => {
    // Trim stray spaces from user input to prevent empty transmissions
    const trimmedInput = input.trim();
    
    // Safety check: Prevent sending if the input is empty OR if an operation is already running
    if (!trimmedInput || isLoading) return;

    // Turn on the loading state to lock inputs and indicate the AI is processing
    setIsLoading(true);

    // Instantly append user text to the chat screen array to show responsiveness
    const updatedMessages = [...messages, { role: "user", content: trimmedInput }];
    setMessages(updatedMessages);
    
    // Clear out the text box immediately so the user can prepare their next message
    setInput("");

    // Memory Guard: Filter out any past network error blocks so they don't pollute LangChain memory
    const historyPayload = messages.filter(msg => msg.role !== 'error'&& 
      !msg.content.includes("Sorry can't process that request"));

    try {
      /**
       * Execute a network POST fetch request to your FastAPI backend server.
       * Node's --env-file flag reads your main folder's .env file and assigns it to process.env.
       */
      const response = await fetch(CHAT_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          prompt: trimmedInput, 
          history: historyPayload 
        })
      });

      // If server returns HTTP 200 Success, extract the data and render it
      //if (response.ok) {
      //  const data = await response.json();
      //  const claraReply = data.response || "";

        // Render the response block inside the speech layout regardless of what it says
      //  setMessages([...updatedMessages, { role: "assistant", content: claraReply }]);
        

      if (response.ok) {
        const data = await response.json();
        const claraReply = data.response || "";
        const audioBase64 = data.audio; // Grab the Base64 audio property from response data

        // Append the message text along with its voice bytes directly to the UI rendering state array
        setMessages([...updatedMessages, { 
          role: "assistant", 
          content: claraReply,
          audio: audioBase64 
        }]);






        // --- SECURE HISTORY CONTROL LOOP ---
        // If the reply text matches our strict refusal statement string, do NOT save this conversation turn!
        if (claraReply === "Sorry, can't process that request for safety reasons.") {
          // This block is left empty purposefully. The message appears on-screen for the user, 
          // but we do not track or append it to our conversational array stack.
        } else {
          // If the interaction is verified and processed cleanly, save both turns to remember context
          messages.push({ role: "user", content: trimmedInput });
          messages.push({ role: "assistant", content: claraReply });
        }
      } else {
        if (response.status===403){setMessages([...updatedMessages, { role: "error", content: "Sorry, can't process that request for safety reasons." }]);}
      else {
        setMessages([...updatedMessages, { role: "error", content: "❌ Backend Error: Unable to fetch response." }]);}
      }
    } catch (error) {
      if (error.status_code===403){setMessages([...updatedMessages, { role: "error", content: "Sorry, can't process that request for safety reasons." }]);}
      else {setMessages([...updatedMessages, { role: "error", content: "🔌 Connection Failure: Server unreachable." }]);}
    } finally {
      setIsLoading(false);
    }
  };

  // Expose the state variables and handler functions to visual components
  return { messages, input, setInput, handleSend, chatBoxRef, isLoading };
}