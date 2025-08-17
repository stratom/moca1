const { exec } = require('child_process');
const path = require('path');

exports.askChatbot = (req, res) => {
  const { question } = req.body;

  if (!question) {
    return res.status(400).json({ error: true, message: "No se envió ninguna pregunta." });
  }

  const scriptPath = path.join(__dirname, '..', '..',  'retrivalai.py');

  const command = `python "${scriptPath}" "${question}"`;

  exec(command, (error, stdout, stderr) => {
    if (error) {
      console.error("❌ Error ejecutando Python:", error.message);
      return res.status(500).json({ error: true, message: error.message });
    }

    if (stderr) {
      console.error("⚠️ stderr de Python:", stderr);
    }

    try {
      const response = stdout.trim();
      res.json({ success: true, question, response });
    } catch (e) {
      console.error("❌ Error procesando salida:", e);
      res.status(500).json({ error: true, message: "Error procesando la respuesta." });
    }
  });
};

