export default function Contact() {
  return (
    <div className="flex flex-col items-center p-6 bg-gray-100">
      <header className="w-full bg-blue-600 text-white py-6">
        <h1 className="text-3xl font-bold text-center">Contact Us</h1>
      </header>
      <section className="w-full max-w-4xl mt-8">
        <img
          src="https://picsum.photos/seed/hero-contact/1200/700"
          alt="A serene workspace environment"
          className="w-full h-auto rounded-lg shadow-lg"
        />
        <h2 className="text-2xl font-semibold mt-4">Get in Touch</h2>
        <p className="mt-2 text-gray-700">
          We are here to assist you with any inquiries you may have regarding our services. Reach out to us through the form below.
        </p>
      </section>
      <section className="w-full max-w-4xl mt-8 p-4 bg-white rounded-lg shadow-md">
        <h2 className="text-xl font-semibold">Contact Form</h2>
        <form className="mt-4">
          <div className="mb-4">
            <label className="block text-gray-700" htmlFor="name">Name</label>
            <input
              type="text"
              id="name"
              className="w-full p-2 border border-gray-300 rounded"
              placeholder="Your Name"
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-gray-700" htmlFor="email">Email</label>
            <input
              type="email"
              id="email"
              className="w-full p-2 border border-gray-300 rounded"
              placeholder="Your Email"
              required
            />
          </div>
          <div className="mb-4">
            <label className="block text-gray-700" htmlFor="message">Message</label>
            <textarea
              id="message"
              className="w-full p-2 border border-gray-300 rounded"
              placeholder="Your Message"
              rows={4}
              required
            />
          </div>
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 transition"
          >
            Send Message
          </button>
        </form>
      </section>
      <section className="w-full max-w-4xl mt-8">
        <h2 className="text-2xl font-semibold">Our Services</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
          <div className="bg-white rounded-lg shadow-md p-4">
            <img
              src="https://picsum.photos/seed/card-contact-1/400/300"
              alt="Service 1 description"
              className="w-full h-auto rounded-lg"
            />
            <h3 className="text-lg font-semibold mt-2">Service One</h3>
            <p className="text-gray-600">Description of service one.</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <img
              src="https://picsum.photos/seed/card-contact-2/400/300"
              alt="Service 2 description"
              className="w-full h-auto rounded-lg"
            />
            <h3 className="text-lg font-semibold mt-2">Service Two</h3>
            <p className="text-gray-600">Description of service two.</p>
          </div>
          <div className="bg-white rounded-lg shadow-md p-4">
            <img
              src="https://picsum.photos/seed/card-contact-3/400/300"
              alt="Service 3 description"
              className="w-full h-auto rounded-lg"
            />
            <h3 className="text-lg font-semibold mt-2">Service Three</h3>
            <p className="text-gray-600">Description of service three.</p>
          </div>
        </div>
      </section>
      <footer className="w-full mt-8 text-center">
        <p className="text-gray-600">© 2023 WorkspaceDirTest. All rights reserved.</p>
      </footer>
    </div>
  );
}
