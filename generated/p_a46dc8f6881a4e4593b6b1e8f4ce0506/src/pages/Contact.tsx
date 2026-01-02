export default function Contact() {
  return (
    <div className="flex flex-col items-center p-6 bg-gray-100">
      <header className="w-full bg-blue-600 text-white py-6">
        <h1 className="text-3xl font-bold text-center">Contact Us</h1>
      </header>
      <section className="mt-8 w-full max-w-4xl">
        <img
          src="https://picsum.photos/seed/hero-contact/1200/700"
          alt="A serene workspace environment"
          className="w-full h-auto rounded-lg shadow-lg"
        />
        <h2 className="text-2xl font-semibold mt-4">Get in Touch</h2>
        <p className="mt-2 text-gray-700">
          We are here to assist you with any inquiries or support you may need. Reach out to us through the form below.
        </p>
      </section>
      <section className="mt-8 w-full max-w-4xl">
        <h2 className="text-2xl font-semibold">Our Services</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-4">
          <div className="bg-white p-4 rounded-lg shadow-md">
            <img
              src="https://picsum.photos/seed/card-contact-1/400/300"
              alt="Service 1 description"
              className="w-full h-32 object-cover rounded-t-lg"
            />
            <h3 className="text-lg font-semibold mt-2">Consultation</h3>
            <p className="text-gray-600">Expert advice tailored to your needs.</p>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-md">
            <img
              src="https://picsum.photos/seed/card-contact-2/400/300"
              alt="Service 2 description"
              className="w-full h-32 object-cover rounded-t-lg"
            />
            <h3 className="text-lg font-semibold mt-2">Workspace Setup</h3>
            <p className="text-gray-600">Creating the perfect environment for productivity.</p>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-md">
            <img
              src="https://picsum.photos/seed/card-contact-3/400/300"
              alt="Service 3 description"
              className="w-full h-32 object-cover rounded-t-lg"
            />
            <h3 className="text-lg font-semibold mt-2">Ongoing Support</h3>
            <p className="text-gray-600">Continuous assistance to ensure your success.</p>
          </div>
        </div>
      </section>
      <section className="mt-8 w-full max-w-4xl">
        <h2 className="text-2xl font-semibold">Contact Form</h2>
        <form className="mt-4 bg-white p-6 rounded-lg shadow-md">
          <div className="mb-4">
            <label htmlFor="name" className="block text-gray-700">Name</label>
            <input
              type="text"
              id="name"
              className="mt-1 block w-full border border-gray-300 rounded-md p-2"
              required
            />
          </div>
          <div className="mb-4">
            <label htmlFor="email" className="block text-gray-700">Email</label>
            <input
              type="email"
              id="email"
              className="mt-1 block w-full border border-gray-300 rounded-md p-2"
              required
            />
          </div>
          <div className="mb-4">
            <label htmlFor="message" className="block text-gray-700">Message</label>
            <textarea
              id="message"
              className="mt-1 block w-full border border-gray-300 rounded-md p-2"
              rows={4}
              required
            />
          </div>
          <button type="submit" className="w-full bg-blue-600 text-white py-2 rounded-md hover:bg-blue-700">
            Send Message
          </button>
        </form>
      </section>
    </div>
  );
}
