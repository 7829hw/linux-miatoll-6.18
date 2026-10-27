// SPDX-License-Identifier: GPL-2.0-only
/*
 * Vulkan shader check for the curtana RAM test.
 *
 * vk-shader-probe [seconds]
 *   1. Draws the triangle.vert/triangle.frag triangle into a 256x256
 *      offscreen image, copies it to a host buffer and checks pixels: the
 *      centre must be shaded (not the black clear colour), the corners must
 *      stay black, and the three vertex colours must reach their corners.
 *   2. Draws the same triangle, rotating, to the panel through VK_KHR_display
 *      for the given time (default 15 s) with FIFO presentation.
 * The SPIR-V is compiled at build time by glslangValidator (triangle_*.h).
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <vulkan/vulkan.h>
#include "triangle_frag.h"
#include "triangle_vert.h"

#define CHECK(call) do { VkResult r_ = (call); if (r_ != VK_SUCCESS) { \
	printf("VK_SHADER_FAIL %s = %d\n", #call, r_); exit(1); } } while (0)
#define STEP(...) do { printf(__VA_ARGS__); printf("\n"); fflush(stdout); } while (0)

struct push { float angle, aspect; };

static VkInstance instance;
static VkPhysicalDevice gpu;
static VkDevice device;
static VkQueue queue;
static uint32_t queue_family;
static VkCommandPool pool;

static uint32_t memory_type(uint32_t bits, VkMemoryPropertyFlags flags)
{
	VkPhysicalDeviceMemoryProperties props;
	uint32_t i;

	vkGetPhysicalDeviceMemoryProperties(gpu, &props);
	for (i = 0; i < props.memoryTypeCount; i++)
		if ((bits & (1u << i)) && (props.memoryTypes[i].propertyFlags & flags) == flags)
			return i;
	printf("VK_SHADER_FAIL no memory type 0x%x\n", flags);
	exit(1);
}

static VkShaderModule shader(const uint32_t *code, size_t size)
{
	VkShaderModuleCreateInfo info = { .sType = VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,
					  .codeSize = size, .pCode = code };
	VkShaderModule module;

	CHECK(vkCreateShaderModule(device, &info, NULL, &module));
	return module;
}

/* One colour attachment that is cleared, drawn and left in final_layout. */
static void make_pipeline(VkFormat format, VkImageLayout final_layout, VkRenderPass *pass, VkPipelineLayout *layout,
			  VkPipeline *pipeline)
{
	VkAttachmentDescription attachment = {
		.format = format, .samples = VK_SAMPLE_COUNT_1_BIT,
		.loadOp = VK_ATTACHMENT_LOAD_OP_CLEAR, .storeOp = VK_ATTACHMENT_STORE_OP_STORE,
		.stencilLoadOp = VK_ATTACHMENT_LOAD_OP_DONT_CARE, .stencilStoreOp = VK_ATTACHMENT_STORE_OP_DONT_CARE,
		.initialLayout = VK_IMAGE_LAYOUT_UNDEFINED, .finalLayout = final_layout,
	};
	VkAttachmentReference reference = { 0, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL };
	VkSubpassDescription subpass = { .pipelineBindPoint = VK_PIPELINE_BIND_POINT_GRAPHICS,
					 .colorAttachmentCount = 1, .pColorAttachments = &reference };
	VkSubpassDependency dependency = {
		.srcSubpass = VK_SUBPASS_EXTERNAL, .dstSubpass = 0,
		.srcStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
		.dstStageMask = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
		.dstAccessMask = VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT,
	};
	VkRenderPassCreateInfo pass_info = { .sType = VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO,
		.attachmentCount = 1, .pAttachments = &attachment, .subpassCount = 1, .pSubpasses = &subpass,
		.dependencyCount = 1, .pDependencies = &dependency };
	VkPushConstantRange range = { VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(struct push) };
	VkPipelineLayoutCreateInfo layout_info = { .sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
		.pushConstantRangeCount = 1, .pPushConstantRanges = &range };
	VkShaderModule vert = shader(triangle_vert, sizeof(triangle_vert));
	VkShaderModule frag = shader(triangle_frag, sizeof(triangle_frag));
	VkPipelineShaderStageCreateInfo stages[2] = {
		{ .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO, .stage = VK_SHADER_STAGE_VERTEX_BIT,
		  .module = vert, .pName = "main" },
		{ .sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO, .stage = VK_SHADER_STAGE_FRAGMENT_BIT,
		  .module = frag, .pName = "main" },
	};
	VkPipelineVertexInputStateCreateInfo input = { .sType = VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO };
	VkPipelineInputAssemblyStateCreateInfo assembly = {
		.sType = VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO,
		.topology = VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST };
	VkPipelineViewportStateCreateInfo viewport = { .sType = VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO,
		.viewportCount = 1, .scissorCount = 1 };
	VkPipelineRasterizationStateCreateInfo raster = {
		.sType = VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO,
		.polygonMode = VK_POLYGON_MODE_FILL, .cullMode = VK_CULL_MODE_NONE, .lineWidth = 1.0f };
	VkPipelineMultisampleStateCreateInfo multisample = {
		.sType = VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO,
		.rasterizationSamples = VK_SAMPLE_COUNT_1_BIT };
	VkPipelineColorBlendAttachmentState blend_attachment = { .colorWriteMask = 0xf };
	VkPipelineColorBlendStateCreateInfo blend = { .sType = VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO,
		.attachmentCount = 1, .pAttachments = &blend_attachment };
	VkDynamicState dynamic_states[2] = { VK_DYNAMIC_STATE_VIEWPORT, VK_DYNAMIC_STATE_SCISSOR };
	VkPipelineDynamicStateCreateInfo dynamic = { .sType = VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO,
		.dynamicStateCount = 2, .pDynamicStates = dynamic_states };
	VkGraphicsPipelineCreateInfo info = { .sType = VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO,
		.stageCount = 2, .pStages = stages, .pVertexInputState = &input, .pInputAssemblyState = &assembly,
		.pViewportState = &viewport, .pRasterizationState = &raster, .pMultisampleState = &multisample,
		.pColorBlendState = &blend, .pDynamicState = &dynamic };

	CHECK(vkCreateRenderPass(device, &pass_info, NULL, pass));
	CHECK(vkCreatePipelineLayout(device, &layout_info, NULL, layout));
	info.layout = *layout;
	info.renderPass = *pass;
	CHECK(vkCreateGraphicsPipelines(device, VK_NULL_HANDLE, 1, &info, NULL, pipeline));
	vkDestroyShaderModule(device, vert, NULL);
	vkDestroyShaderModule(device, frag, NULL);
}

static void record_draw(VkCommandBuffer cmd, VkRenderPass pass, VkFramebuffer framebuffer, VkPipelineLayout layout,
			VkPipeline pipeline, VkExtent2D extent, struct push push)
{
	VkClearValue clear = { .color = { .float32 = { 0, 0, 0, 1 } } };
	VkRenderPassBeginInfo begin = { .sType = VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO,
		.renderPass = pass, .framebuffer = framebuffer, .renderArea = { { 0, 0 }, extent },
		.clearValueCount = 1, .pClearValues = &clear };
	VkViewport viewport = { 0, 0, extent.width, extent.height, 0, 1 };
	VkRect2D scissor = { { 0, 0 }, extent };

	vkCmdBeginRenderPass(cmd, &begin, VK_SUBPASS_CONTENTS_INLINE);
	vkCmdBindPipeline(cmd, VK_PIPELINE_BIND_POINT_GRAPHICS, pipeline);
	vkCmdSetViewport(cmd, 0, 1, &viewport);
	vkCmdSetScissor(cmd, 0, 1, &scissor);
	vkCmdPushConstants(cmd, layout, VK_SHADER_STAGE_VERTEX_BIT, 0, sizeof(push), &push);
	vkCmdDraw(cmd, 3, 1, 0, 0);
	vkCmdEndRenderPass(cmd);
}

static void submit_and_wait(VkCommandBuffer cmd, VkSemaphore wait, VkSemaphore signal)
{
	VkPipelineStageFlags stage = VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
	VkSubmitInfo submit = { .sType = VK_STRUCTURE_TYPE_SUBMIT_INFO,
		.waitSemaphoreCount = wait ? 1 : 0, .pWaitSemaphores = &wait, .pWaitDstStageMask = &stage,
		.commandBufferCount = 1, .pCommandBuffers = &cmd,
		.signalSemaphoreCount = signal ? 1 : 0, .pSignalSemaphores = &signal };
	VkFenceCreateInfo fence_info = { .sType = VK_STRUCTURE_TYPE_FENCE_CREATE_INFO };
	VkFence fence;

	CHECK(vkCreateFence(device, &fence_info, NULL, &fence));
	CHECK(vkQueueSubmit(queue, 1, &submit, fence));
	CHECK(vkWaitForFences(device, 1, &fence, VK_TRUE, 5000000000ull));
	vkDestroyFence(device, fence, NULL);
}

static VkImageView view_of(VkImage image, VkFormat format)
{
	VkImageViewCreateInfo info = { .sType = VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO, .image = image,
		.viewType = VK_IMAGE_VIEW_TYPE_2D, .format = format,
		.subresourceRange = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1 } };
	VkImageView view;

	CHECK(vkCreateImageView(device, &info, NULL, &view));
	return view;
}

static VkFramebuffer framebuffer_of(VkRenderPass pass, VkImageView view, VkExtent2D extent)
{
	VkFramebufferCreateInfo info = { .sType = VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO, .renderPass = pass,
		.attachmentCount = 1, .pAttachments = &view, .width = extent.width, .height = extent.height, .layers = 1 };
	VkFramebuffer framebuffer;

	CHECK(vkCreateFramebuffer(device, &info, NULL, &framebuffer));
	return framebuffer;
}

static int offscreen_test(VkCommandBuffer cmd)
{
	const VkFormat format = VK_FORMAT_R8G8B8A8_UNORM;
	const VkExtent2D extent = { 256, 256 };
	VkImageCreateInfo image_info = { .sType = VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO, .imageType = VK_IMAGE_TYPE_2D,
		.format = format, .extent = { 256, 256, 1 }, .mipLevels = 1, .arrayLayers = 1,
		.samples = VK_SAMPLE_COUNT_1_BIT, .tiling = VK_IMAGE_TILING_OPTIMAL,
		.usage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT | VK_IMAGE_USAGE_TRANSFER_SRC_BIT };
	VkBufferCreateInfo buffer_info = { .sType = VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO, .size = 256 * 256 * 4,
		.usage = VK_BUFFER_USAGE_TRANSFER_DST_BIT };
	VkMemoryAllocateInfo alloc = { .sType = VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO };
	VkCommandBufferBeginInfo begin = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
	VkBufferImageCopy copy = { .imageSubresource = { VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1 },
				   .imageExtent = { 256, 256, 1 } };
	VkMemoryRequirements req;
	VkDeviceMemory image_memory, buffer_memory;
	VkRenderPass pass;
	VkPipelineLayout layout;
	VkPipeline pipeline;
	VkFramebuffer framebuffer;
	VkImageView view;
	VkBuffer buffer;
	VkImage image;
	const uint8_t *px;
	int bad = 0;

	make_pipeline(format, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, &pass, &layout, &pipeline);
	CHECK(vkCreateImage(device, &image_info, NULL, &image));
	vkGetImageMemoryRequirements(device, image, &req);
	alloc.allocationSize = req.size;
	alloc.memoryTypeIndex = memory_type(req.memoryTypeBits, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
	CHECK(vkAllocateMemory(device, &alloc, NULL, &image_memory));
	CHECK(vkBindImageMemory(device, image, image_memory, 0));
	CHECK(vkCreateBuffer(device, &buffer_info, NULL, &buffer));
	vkGetBufferMemoryRequirements(device, buffer, &req);
	alloc.allocationSize = req.size;
	alloc.memoryTypeIndex = memory_type(req.memoryTypeBits, VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
					    VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
	CHECK(vkAllocateMemory(device, &alloc, NULL, &buffer_memory));
	CHECK(vkBindBufferMemory(device, buffer, buffer_memory, 0));
	view = view_of(image, format);
	framebuffer = framebuffer_of(pass, view, extent);

	CHECK(vkBeginCommandBuffer(cmd, &begin));
	record_draw(cmd, pass, framebuffer, layout, pipeline, extent, (struct push){ 0.0f, 1.0f });
	vkCmdCopyImageToBuffer(cmd, image, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL, buffer, 1, &copy);
	CHECK(vkEndCommandBuffer(cmd));
	submit_and_wait(cmd, VK_NULL_HANDLE, VK_NULL_HANDLE);
	CHECK(vkMapMemory(device, buffer_memory, 0, VK_WHOLE_SIZE, 0, (void **)&px));

#define PIXEL(x, y) (px + ((y) * 256 + (x)) * 4)
	{
		/* Vertices at (0,-0.6), (0.52,0.3), (-0.52,0.3) in NDC: top, bottom right, bottom left. */
		static const struct { const char *name; int x, y, want; } probes[] = {
			{ "centre", 128, 128, -1 }, { "corner", 2, 2, 0 }, { "corner", 253, 253, 0 },
			{ "near-red-vertex", 128, 60, 0 }, { "near-green-vertex", 184, 161, 1 },
			{ "near-blue-vertex", 72, 161, 2 },
		};
		unsigned int i;

		for (i = 0; i < sizeof(probes) / sizeof(probes[0]); i++) {
			const uint8_t *p = PIXEL(probes[i].x, probes[i].y);
			int ok;

			if (probes[i].want == -1)
				ok = p[0] + p[1] + p[2] > 150;
			else if (!strcmp(probes[i].name, "corner"))
				ok = p[0] + p[1] + p[2] == 0;
			else
				ok = p[probes[i].want] > 150 && p[probes[i].want] >= p[0] && p[probes[i].want] >= p[1] &&
				     p[probes[i].want] >= p[2];
			printf("pixel %-17s (%3d,%3d) rgba=%3u,%3u,%3u,%3u %s\n", probes[i].name, probes[i].x, probes[i].y,
			       p[0], p[1], p[2], p[3], ok ? "ok" : "BAD");
			bad += !ok;
		}
	}
	vkUnmapMemory(device, buffer_memory);
	vkDestroyFramebuffer(device, framebuffer, NULL);
	vkDestroyImageView(device, view, NULL);
	vkDestroyImage(device, image, NULL);
	vkDestroyBuffer(device, buffer, NULL);
	vkFreeMemory(device, image_memory, NULL);
	vkFreeMemory(device, buffer_memory, NULL);
	vkDestroyPipeline(device, pipeline, NULL);
	vkDestroyPipelineLayout(device, layout, NULL);
	vkDestroyRenderPass(device, pass, NULL);
	return bad;
}

int main(int argc, char **argv)
{
	const char *instance_ext[] = { VK_KHR_SURFACE_EXTENSION_NAME, VK_KHR_DISPLAY_EXTENSION_NAME };
	const char *device_ext[] = { VK_KHR_SWAPCHAIN_EXTENSION_NAME };
	VkApplicationInfo app = { .sType = VK_STRUCTURE_TYPE_APPLICATION_INFO,
				  .pApplicationName = "vk-shader-probe", .apiVersion = VK_API_VERSION_1_1 };
	VkInstanceCreateInfo instance_info = { .sType = VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO,
		.pApplicationInfo = &app, .enabledExtensionCount = 2, .ppEnabledExtensionNames = instance_ext };
	float priority = 1.0f;
	VkDeviceQueueCreateInfo queue_info = { .sType = VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,
		.queueCount = 1, .pQueuePriorities = &priority };
	VkDeviceCreateInfo device_info = { .sType = VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,
		.queueCreateInfoCount = 1, .pQueueCreateInfos = &queue_info,
		.enabledExtensionCount = 1, .ppEnabledExtensionNames = device_ext };
	VkCommandPoolCreateInfo pool_info = { .sType = VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,
		.flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT };
	VkCommandBufferAllocateInfo cmd_info = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,
		.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY, .commandBufferCount = 1 };
	VkSemaphoreCreateInfo sem_info = { .sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO };
	VkQueueFamilyProperties families[8];
	VkPhysicalDeviceProperties props;
	VkDisplayPropertiesKHR display;
	VkDisplayModePropertiesKHR mode;
	VkSurfaceCapabilitiesKHR caps;
	VkSurfaceFormatKHR formats[16];
	VkImage images[8];
	VkImageView views[8];
	VkFramebuffer framebuffers[8];
	VkRenderPass pass;
	VkPipelineLayout layout;
	VkPipeline pipeline;
	VkSurfaceKHR surface;
	VkSwapchainKHR swapchain;
	VkSemaphore acquired, rendered;
	VkCommandBuffer cmd;
	uint32_t count, i, frames = 0, seconds = argc > 1 ? atoi(argv[1]) : 15;
	struct timespec start, now;
	int bad;

	STEP("step instance");
	CHECK(vkCreateInstance(&instance_info, NULL, &instance));
	count = 1;
	vkEnumeratePhysicalDevices(instance, &count, &gpu);
	vkGetPhysicalDeviceProperties(gpu, &props);
	printf("gpu %s\n", props.deviceName);
	count = 8;
	vkGetPhysicalDeviceQueueFamilyProperties(gpu, &count, families);
	for (queue_family = 0; queue_family < count; queue_family++)
		if (families[queue_family].queueFlags & VK_QUEUE_GRAPHICS_BIT)
			break;
	queue_info.queueFamilyIndex = queue_family;
	CHECK(vkCreateDevice(gpu, &device_info, NULL, &device));
	vkGetDeviceQueue(device, queue_family, 0, &queue);
	pool_info.queueFamilyIndex = queue_family;
	CHECK(vkCreateCommandPool(device, &pool_info, NULL, &pool));
	cmd_info.commandPool = pool;
	CHECK(vkAllocateCommandBuffers(device, &cmd_info, &cmd));

	STEP("step offscreen triangle");
	bad = offscreen_test(cmd);
	if (bad) {
		printf("VK_SHADER_FAIL offscreen pixels bad=%d\n", bad);
		return 1;
	}
	STEP("VK_SHADER_OFFSCREEN_OK");

	STEP("step display");
	count = 1;
	CHECK(vkGetPhysicalDeviceDisplayPropertiesKHR(gpu, &count, &display));
	count = 1;
	CHECK(vkGetDisplayModePropertiesKHR(gpu, display.display, &count, &mode));
	{
		VkDisplaySurfaceCreateInfoKHR info = { .sType = VK_STRUCTURE_TYPE_DISPLAY_SURFACE_CREATE_INFO_KHR,
			.displayMode = mode.displayMode, .planeIndex = 0, .transform = VK_SURFACE_TRANSFORM_IDENTITY_BIT_KHR,
			.alphaMode = VK_DISPLAY_PLANE_ALPHA_OPAQUE_BIT_KHR, .imageExtent = mode.parameters.visibleRegion };

		CHECK(vkCreateDisplayPlaneSurfaceKHR(instance, &info, NULL, &surface));
	}
	CHECK(vkGetPhysicalDeviceSurfaceCapabilitiesKHR(gpu, surface, &caps));
	count = 16;
	CHECK(vkGetPhysicalDeviceSurfaceFormatsKHR(gpu, surface, &count, formats));
	{
		VkSwapchainCreateInfoKHR info = { .sType = VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR,
			.surface = surface, .minImageCount = caps.minImageCount < 2 ? 2 : caps.minImageCount,
			.imageFormat = formats[0].format, .imageColorSpace = formats[0].colorSpace,
			.imageExtent = caps.currentExtent, .imageArrayLayers = 1,
			.imageUsage = VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT, .imageSharingMode = VK_SHARING_MODE_EXCLUSIVE,
			.preTransform = caps.currentTransform, .compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
			.presentMode = VK_PRESENT_MODE_FIFO_KHR, .clipped = VK_TRUE };

		CHECK(vkCreateSwapchainKHR(device, &info, NULL, &swapchain));
	}
	count = 8;
	CHECK(vkGetSwapchainImagesKHR(device, swapchain, &count, images));
	make_pipeline(formats[0].format, VK_IMAGE_LAYOUT_PRESENT_SRC_KHR, &pass, &layout, &pipeline);
	for (i = 0; i < count; i++) {
		views[i] = view_of(images[i], formats[0].format);
		framebuffers[i] = framebuffer_of(pass, views[i], caps.currentExtent);
	}
	CHECK(vkCreateSemaphore(device, &sem_info, NULL, &acquired));
	CHECK(vkCreateSemaphore(device, &sem_info, NULL, &rendered));
	printf("display %ux%u format=%d images=%u\n", caps.currentExtent.width, caps.currentExtent.height,
	       formats[0].format, count);

	STEP("step present %us", seconds);
	clock_gettime(CLOCK_MONOTONIC, &start);
	for (;;) {
		VkCommandBufferBeginInfo begin = { .sType = VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO };
		VkPresentInfoKHR present = { .sType = VK_STRUCTURE_TYPE_PRESENT_INFO_KHR,
			.waitSemaphoreCount = 1, .pWaitSemaphores = &rendered, .swapchainCount = 1,
			.pSwapchains = &swapchain };
		uint32_t index;
		double elapsed;

		clock_gettime(CLOCK_MONOTONIC, &now);
		elapsed = (now.tv_sec - start.tv_sec) + (now.tv_nsec - start.tv_nsec) / 1e9;
		if (elapsed >= seconds)
			break;
		CHECK(vkAcquireNextImageKHR(device, swapchain, 5000000000ull, acquired, VK_NULL_HANDLE, &index));
		CHECK(vkResetCommandBuffer(cmd, 0));
		CHECK(vkBeginCommandBuffer(cmd, &begin));
		record_draw(cmd, pass, framebuffers[index], layout, pipeline, caps.currentExtent,
			    (struct push){ (float)elapsed * 1.5f,
					   (float)caps.currentExtent.width / caps.currentExtent.height });
		CHECK(vkEndCommandBuffer(cmd));
		submit_and_wait(cmd, acquired, rendered);
		present.pImageIndices = &index;
		CHECK(vkQueuePresentKHR(queue, &present));
		frames++;
	}
	printf("presented frames=%u in %us (%.1f fps)\n", frames, seconds, frames / (double)seconds);
	vkDeviceWaitIdle(device);
	printf("VK_SHADER_OK\n");
	return 0;
}
